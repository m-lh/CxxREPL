#include <iostream>
#include <typeinfo>

extern int a;
int& b=a;


extern "C" void work(){
    ++b;
    std::cout<< "[#] s3 start" << std::endl;
    std::cout<< "[#] a" << typeid(a).name() << ":" << a << std::endl;
    std::cout<< "[#] b" << typeid(b).name() << ":" << b << std::endl;
}

// __attribute__((constructor)) void s3start(){
//     std::cout<< "[#] s3 start" << std::endl;
//     std::cout<< "[#] a" << typeid(a).name() << ":" << a << std::endl;
//     std::cout<< "[#] b" << typeid(b).name() << ":" << b << std::endl;

// }