#include <stdio.h>

int foo();

int a = foo();

__attribute__((constructor)) void s2start(){
    printf("[#] in s2.cpp a=%d\n", a);
}