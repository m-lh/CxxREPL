#include <stdio.h>
#include <dlfcn.h>

#include <string>

extern int a;
extern int b;

using work_type = void(*)();

void* load(std::string name){
    
    void* h1 = dlopen(name.c_str(), RTLD_NOW|RTLD_GLOBAL);
    if(!h1){
        fprintf(stderr, "%s\n", dlerror());
    }
    dlerror();
    if (h1){
        printf("[#] %s loaded\n", name.c_str());
    }
    else{
        printf("[!] %s load failed!\n", name.c_str());
        return nullptr;
    }


    void* p_work = dlsym(h1, "work");
    if(p_work) printf("[#] work func loaded\n");
    work_type work = reinterpret_cast<work_type>(p_work) ;
    // work_type work = (work_type)(dlsym(h1, "work")) ;
    if(work){
        printf("[#] work func loaded\n");
        work();
    }
    return h1;
}

int main(int argc, char const *argv[])
{
    load("./libs1.so");
    load("./libs2.so");
    load("./libs3.so");
    load("./libs4.so");
    load("./libs5.so");

    return 0;
}
