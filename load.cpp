#include <stdio.h>
#include <dlfcn.h>

using work_type = void(*)();

extern "C" int load(char* name, /* out */ void** phandle){
    
    void* handle = dlopen(name, RTLD_NOW|RTLD_GLOBAL);
    *phandle = handle;
    if(!handle){
        fprintf(stderr, "%s\n", dlerror());
        return -1;
    }

    work_type work = reinterpret_cast<work_type>(dlsym(handle, "work")) ;
    if(work){
        // printf("[#] work func loaded\n");
        work();
    }
    return 0;
}
