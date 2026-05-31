from tests.codegen.utils import compile_to_assembly


def test_prologue_and_epilogue_are_generated():
    asm = compile_to_assembly("""
fn main() int {
    return 5;
}
""")
    assert "section .text" in asm
    assert "global main" in asm
    assert "main:" in asm
    assert "push rbp" in asm
    assert "mov rbp, rsp" in asm
    assert "mov rsp, rbp" in asm
    assert "pop rbp" in asm
    assert "ret" in asm


def test_arithmetic_ir_maps_to_x86_instructions():
    asm = compile_to_assembly("""
fn main() int {
    int x = 2 + 3 * 4;
    return x;
}
""")
    assert "imul eax" in asm
    assert "add eax" in asm
    assert "mov dword [rbp-" in asm


def test_comparison_and_control_flow_map_to_x86():
    asm = compile_to_assembly("""
fn main() int {
    int x = 1;
    if (x > 0) {
        return 7;
    }
    return 3;
}
""")
    assert "cmp eax" in asm
    assert "setg al" in asm
    assert "jne .LBB_main_" in asm
    assert "jmp .L" in asm


def test_function_call_uses_system_v_argument_registers():
    asm = compile_to_assembly("""
fn add(a int, b int) int {
    return a + b;
}

fn main() int {
    return add(2, 3);
}
""")
    assert "mov edi, eax" in asm
    assert "mov esi, eax" in asm
    assert "call add" in asm
