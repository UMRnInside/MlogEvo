extern struct MlogObject switch1, display1;
double pos_x = 40.0, pos_y = 40.0;
double router_size = 40.0, router_rotation = 45.0;

void main() {
    int should_draw_router;
    // It's recommended to use `volatile` qualifier
    // on blocks that has no input/output, but produces side effects.
    // https://gcc.gnu.org/onlinedocs/gcc/Extended-Asm.html#Volatile
    //__asm__ volatile ("draw clear 0 0 0 0 0 0");
    __asm__ (
            "draw clear 0 0 0 0 0 0\n"
            "sensor %0 %1 @enabled"
            : "=r" (should_draw_router)
            /* mlog does NOT have registers though */
            : "r" (switch1)
    );
    if (should_draw_router) {
        __asm__ (
                "draw image %0 %1 @router %2 %3 0"
                : /* no output */
                : "r" (pos_x), "r" (pos_y), "r" (router_size), "r" (router_rotation)
        );
    }
    __asm__ volatile (
            "drawflush %0"
            : /* no output */
            : "r" (display1)
    );
}
