; MiniCompiler Sprint 5 runtime library
; NASM syntax, Linux x86-64 syscalls, System V AMD64 ABI

default rel
section .data
    division_by_zero_msg db "runtime error: division by zero", 10
    division_by_zero_len equ $ - division_by_zero_msg

section .bss
    input_buffer resb 64
    print_buffer resb 32

section .text
global _start
global print_int
global print_string
global read_int
global exit
global __minic_division_by_zero
extern main

_start:
    call main
    mov edi, eax
    call exit

; exit(status: rdi)
exit:
    mov eax, 60
    syscall

; print_string(rdi = null-terminated string pointer)
print_string:
    push rbp
    mov rbp, rsp
    push rbx
    mov rbx, rdi
    xor edx, edx
.len_loop:
    cmp byte [rbx + rdx], 0
    je .write
    inc rdx
    jmp .len_loop
.write:
    mov eax, 1
    mov edi, 1
    mov rsi, rbx
    syscall
    pop rbx
    mov rsp, rbp
    pop rbp
    ret

; print_int(edi = signed integer)
print_int:
    push rbp
    mov rbp, rsp
    push rbx
    push r12

    mov eax, edi
    lea rsi, [print_buffer + 31]
    mov byte [rsi], 10          ; trailing newline
    mov ecx, 1                 ; length
    mov ebx, 10
    xor r12d, r12d             ; negative flag

    cmp eax, 0
    jge .convert
    neg eax
    mov r12d, 1

.convert:
    dec rsi
    xor edx, edx
    div ebx
    add dl, '0'
    mov [rsi], dl
    inc ecx
    test eax, eax
    jne .convert

    cmp r12d, 0
    je .write
    dec rsi
    mov byte [rsi], '-'
    inc ecx

.write:
    mov eax, 1
    mov edi, 1
    mov edx, ecx
    syscall

    pop r12
    pop rbx
    mov rsp, rbp
    pop rbp
    ret

; read_int() -> eax
read_int:
    push rbp
    mov rbp, rsp
    mov eax, 0
    mov edi, 0
    lea rsi, [input_buffer]
    mov edx, 63
    syscall

    lea rsi, [input_buffer]
    xor eax, eax
    xor ecx, ecx               ; sign flag
    cmp byte [rsi], '-'
    jne .parse
    mov ecx, 1
    inc rsi
.parse:
    movzx edx, byte [rsi]
    cmp dl, '0'
    jb .done
    cmp dl, '9'
    ja .done
    imul eax, eax, 10
    sub edx, '0'
    add eax, edx
    inc rsi
    jmp .parse
.done:
    cmp ecx, 0
    je .ret
    neg eax
.ret:
    mov rsp, rbp
    pop rbp
    ret

; Runtime trap used by generated code before signed division.
__minic_division_by_zero:
    mov eax, 1
    mov edi, 2
    lea rsi, [division_by_zero_msg]
    mov edx, division_by_zero_len
    syscall
    mov edi, 136
    call exit
