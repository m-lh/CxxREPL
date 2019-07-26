#!python
import os
import string
import logging
from pprint import pprint
from subprocess import getstatusoutput

from ctypes import cdll, c_void_p, pointer

# logging.basicConfig(level=logging.DEBUG)

plugin = cdll.LoadLibrary("./libload.so")
logging.info('LoadLibrary("./libload.so") -> %s', plugin)

handle = c_void_p(0)

def parse_clang_error(err):
    res = []
    for line in err.splitlines():
        if ': error:' in line:
            filename, lineno, col, error, infostr = line.split(":", 4)
            res.append((filename, lineno, col, error, infostr))
    return res

symbols = {}

def need_more(line):
    line = line.strip()
    if not line:
        return False
    if line.endswith("\\"):
        return True
    if line.startswith('#include'):
        return False
    if line.startswith('#'):
        raise Exception("Unkonw need more")
    if line.startswith("class") or line.startswith("struct") or line.startswith("union"):
        return line.endswith(";")

    stack = []

    for c in line:
        if c in {'{', '[', '('}:
            stack.append(c)
        elif c in {'}', ']', ')'}:
            cc = stack.pop()
            assert {'}':'{', '>':'<', ']':'[', ')':'('}[c] == cc, line
        
    if len(stack) != 0:
        return True

    if line.rstrip()[-1] in {';', '}'}:
        return False
    
    return False

def parse_decl(line):
    """
    return name and decl
    eg. int a=1; return ("a", "extern int a;")
    """
    if line.startswith("#include"):
        return None, line
    if line.startswith("using "):
        return None, line
    if line.startswith("class "):
        return None, line
    if line.startswith("template "):
        return None, line

    stack = []
    seen = []
    text = []

    for index, char in enumerate(line):
        if char in "_" + string.ascii_letters :
            text.append(char)
        else:
            if not stack and text:
                seen.append(("text", ''.join(text)))
            text.clear()

        if char == "=":
            # type name = init;
            if len(stack) == 0:
                decl, init = line.split('=', 1)
                name = decl.split()[-1]
                # auto name = init;
                if 'auto' in decl:
                    init = init.strip()
                    if init[-1] == ';':
                        init = init[:-1]
                    if init.startswith('['):
                        return name, line
                    decl = decl.replace('auto', f'decltype({init})')
                return name, 'extern ' + decl + ';'
        elif char == '{':
            if len(stack) == 0:
                if seen and seen[-1] == ("(", ")"):
                    decl, init = line.split('{', 1)
                    return None, decl+';'
                else:
                    decl, init = line.split('{', 1)
                    tp, name = decl.rsplit(" ", 1)
                    return name, 'extern ' + decl + ';'
            else:
                stack.append(char)
        elif char in {'{', '[', '('}:
            stack.append(char)
        elif char in {'}', ']', ')'}:
            cc = stack.pop()
            assert {'}':'{', '>':'<', ']':'[', ')':'('}[char] == cc, line
            if not stack:
                seen.append((cc, char))
        elif char == '<':
            if len(stack) == 0:
                stack.append(char)
        elif char == '>':
            if stack and stack[-1] == '<':
                stack.pop()
        elif char == ';':
            if len(stack) == 0:
                return None, 'extern ' + line



    return None, None

def need_show(line):
    if need_more(line):
        return False
    l = line.strip()
    if l[0] in "#":
        return False
    if l[-1] not in ";}":
        return True
    else:
        return False

class CompileContext:
    _i = 1

    def __init__(self):
        self._decls = ['#include "./common.hpp"']
        self._cache_so_name = None
        self._errors = {}

    def _try_compile(self, line):
        i = self._i
        self._i += 1
        cpp_name = f"./temp/s{i}.cpp"
        so_name = f"./temp/libs{i}.so"

        lines = self._decls + [line]
        with open(cpp_name, "w") as f:
            f.write("\n".join(lines))
        
        cmd = f"clang++ {cpp_name} -g -std=c++11 -I. -I/mnt/d/boost_1_67_0 -shared -fPIC -o {so_name}"
        ret, output = getstatusoutput(cmd)
        self._cache_so_name = so_name
        logging.debug("[#] run command `%s` -> `%s`", cmd, ret)
        if ret != 0:
            logging.debug("[#] output is %s", output)
        errs = parse_clang_error(output)
        return ret, errs[0] if errs else None

    def load_cache(self):
        plugin.load(self._cache_so_name.encode(), pointer(handle))

    def update_decls(self, line):
        name, decl = parse_decl(line)
        if decl and self._try_compile(decl):
            self._decls.append(decl) 
        else:
            logging.error("[!] update_decls `%s` error", decl)
                
        if name:
            symbols[name] = decl
            logging.debug("add symbol `%s` to symbol table", name)

    def is_decl(self, line):
        if need_show(line):
            return False
        ret, err = self._try_compile(line)
        if err:
            self._errors['decl'] = err
        return ret == 0

    def is_decl_print(self, line):
        is_need_semi = self._errors.get("decl", [""])[-1].strip().startswith("expected ';' after top level declarator")
        if not is_need_semi and not need_show(line):
            return False
        name, decl = parse_decl(line)
        if not is_need_semi and not name:
            return False
        assert name, f"parse_decl({line!r}) -> (name={name}, decl={decl})"
        ret, err =  self._try_compile(f'{line};\nextern "C" void work(){{\n    std::cout<< "(" << boost::typeindex::type_id<decltype({name})>().pretty_name() << ")" << {name} << std::endl;\n}}');
        if err:
            self._errors['decl_print'] = err
        return ret == 0

    def is_expr(self, line):
        if need_show(line):
            return False
        ret, err =  self._try_compile(f'extern "C" void work(){{\n    {line}\n}}');
        if err:
            self._errors['expr'] = err
        return ret == 0

    def is_expr_print(self, line):
        if not need_show(line):
            return False
        ret, err = self._try_compile(f'extern "C" void work(){{\n    std::cout<< "(" << boost::typeindex::type_id<decltype({line})>().pretty_name() << ")" << {line} << std::endl;\n}}');
        if err:
            self._errors['expr_print'] = err
        return ret == 0

    def run(self, line):
        self._errors.clear()
        if self.is_decl(line):
            logging.debug("is_decl")
            self.load_cache()
            self.update_decls(line)

        elif self.is_decl_print(line):
            logging.debug("is_decl_print")
            self.load_cache()
            self.update_decls(line)

        elif self.is_expr(line):
            logging.debug("is_expr")
            self.load_cache()

        elif self.is_expr_print(line):
            logging.debug("is_expr_print")
            self.load_cache()

        else:
            logging.error("unkonw type `%s`", line)
            pprint(self._errors)


def test():
    ctx = CompileContext()
    while True:
        line = input("C++ > ")
        if not line.strip():
            continue
        if line.startswith("py "):
            print(eval(line[2:].strip()))
            continue
        while need_more(line):
            line += '\n' + input("C++.. ")
        
        ctx.run(line)

    
if __name__ == "__main__":
    test()