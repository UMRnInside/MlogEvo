# MlogEvo "cdecl-like" Calling Convention
It can be called as *cdecl*, in mlog though.

**Do not** push Mlog native objects into memory, the memory blocks can only store numbers.

## Overview
```
LOW +---------------------------------------+ HIGH
    | Heap -> |         | <- Stack | static |
LOW +---------------------------------------+ HIGH
```
The heap can be implemented as a memory pool. That is, moving the "growing" heap into static area.

## Address Space for a Function
```
    <-- Stack
LOW +----------------------+------------+-----------+----+ HIGH
    ^ (variables in stack) ^            ^           ^ 
    |                      |            |           |
    Stack top              Stack frame  Arguments   Stack top
                                        (if any)    (of the caller)
```

## Variables
(Names in mlog)
* `mevStackTop`: Points to stack top, decreases by 1-word on stack push event.
    * `mevStack[mevStackTop--] = somethingToPush;`
* `mevFramePtr`: Points to the beginning of current stack frame
* `mevResultPtr`: A callee writes its return value to where `mevResultPtr` points to.
* `mevReturnAddr`: Stores the return address. 

## Stack frame

The stack frame is a simple 3-word-long structure. It's created to restore _caller's_ state.

| Offset               | 0             | 1               | 2               |
|----------------------|---------------|-----------------|-----------------|
| Content (for caller) | `mevFramePtr` | `mevReturnAddr` | `mevResultAddr` |

If a function does not have a return value, the `result address` will not be used.

## Calling a "cdecl-like" Function
1. Start calling.
2. Push arguments *from right to left* into the stack.
3. Create stack frame to save current `mevReturnAddr` and `mevResultAddr`
4. Set new `mevReturnAddr` and `mevResultAddr` for callee.
5. Call that function. This can be done by jumping or setting `@counter`
    * The callee cleans its stack, if it used any.
6. Pop arguments out.
7. Done calling.

## Returning from a "cdecl-like" Function
1. Write result into where `mevResultPtr` points to, if any.
2. Pop local stack variables out of the stack
    * just modify the `mevStackTop`
3. Recover `mevFramePtr` (of caller) from current stack frame
4. Return to `mevReturnAddr` by setting `@counter` in mlog.