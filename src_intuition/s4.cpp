#include <iostream>
extern int a;
extern int& b;
void print() { std::cout << a << std::endl; }
void print_b() { std::cout << b << std::endl; }