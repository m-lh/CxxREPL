void print();
void print_b();

__attribute__((constructor)) void s5start(){
    print();
    print_b();
}