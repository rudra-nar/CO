import sys
registers = [0,0,380,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0] #for stack pointer
PC = 0
Memory_address = {}
overflow = pow(2,32)

temp_memory_address = {}

opcode_instruction = {
    "0110011" : "R_Type",
    "0000011" : "I_Type",
    "0010011" : "I_Type",
    "1100111" : "I_Type",
    "0100011" : "S_Type",
    "1100011" : "B_Type",
    "1101111" : "J_Type"
}
def decimal_to_32bit(num):
    if num < 0:
        num = (1 << 32) + num  # Convert negative numbers to two's complement
    
    binary_rep = format(num %overflow, '#034b')  # Ensure 32-bit output with '0b' prefix
    return binary_rep

def to_signed(x):
    if x >= 2**31:
        return x - 2**32
    return x

def sign_extend(bin_str, bits):
    value = int(bin_str, 2)
    if bin_str[0] == '1':  # negative number
        value -= (1 << len(bin_str))
    return value



def init_memory_address(Memory_address):
    i = 65536
    while i <= 65660:
        hex_string = format(i, '08X')
        Memory_address[f"0x{hex_string}"] = 0
        i+=4
    # for i in Memory_address:
    #     print(i, Memory_address[i])



def type_of_instruction(line, Memory_address, registers):
    trace_array = []
    new_trace_array=  []
    global PC
    halt = 0
    opcode = line[25:32]
    # print(opcode)
    if opcode in opcode_instruction:
        if opcode_instruction[opcode] == "R_Type":
            # PC+=4
            # print(PC, registers)
            PC = simulate_R_type(line, registers, Memory_address)
            # print(PC, registers)
            # print(new_PC)
            # PC = new_PC
        elif opcode_instruction[opcode] == "I_Type":
            PC = simulate_I_type(line, registers, Memory_address)
        elif opcode_instruction[opcode] == "S_Type":
            PC = simulate_S_type(line, registers, Memory_address)
        elif opcode_instruction[opcode] == "B_Type":
            PC, halt = simulate_B_type(line, registers, Memory_address)
        elif opcode_instruction[opcode] == "J_Type":
            PC = simulate_J_type(line, registers, Memory_address)
    else:
        raise Exception("Unsupported type of instruction")
    # print(line, end = " ")
    if (halt):
        trace_array.append(decimal_to_32bit(PC-4))
        new_trace_array.append(PC-4)
        # print(decimal_to_32bit(PC-4), end = " ")
        for i in registers:
            trace_array.append(decimal_to_32bit(i))
            new_trace_array.append(i)
            # print(decimal_to_32bit(i), end = " ")
        # print("")
        return new_trace_array, trace_array, True
    trace_array.append(decimal_to_32bit(PC))
    new_trace_array.append(PC)
    # print(decimal_to_32bit(PC), end = " ")
    for i in registers:
        trace_array.append(decimal_to_32bit(i))
        new_trace_array.append(i)
        # print(decimal_to_32bit(i), end = " ")
    # print("")
    return new_trace_array, trace_array, False

def simulate_R_type(line, registers, Memory_address):
    global PC
    func3 = line[17:20]
    func7 = line[0:7]
    rs2 = int(line[7:12], 2)
    rs1   = int(line[12:17], 2)
    rd    = int(line[20:25], 2)
    if (func3 == "000" and func7 == "0000000" and rd != 0):
        # print("add")
        registers[rd] = (registers[rs1] + registers[rs2])%overflow
    elif (func3 == "000" and func7 == "0100000" and rd != 0):
        # print("sub")
        registers[rd] = (registers[rs1] - registers[rs2])%overflow
    elif (func3 == "010" and rd != 0):
        # print("slt")
        if (to_signed(registers[rs1]) < to_signed(registers[rs2])):
            registers[rd] = 1
        else:
            registers[rd] = 0
    elif (func3 == "101" and rd != 0):
        # print("srl")
        temp = registers[rs2] % 16
        registers[rd] = (registers[rs1] >> temp) %overflow
    elif (func3 == "110" and rd != 0):
        # print("or")
        registers[rd] = registers[rs1] | registers[rs2]
    elif (func3 == "111" and rd != 0):
        # print("and")
        registers[rd] = registers[rs1] & registers[rs2]
    else:
        raise Exception("Unsupported R-type instruction")
    # print(line, rd, rs1, rs2)
    # print(PC+4)
    return PC + 4

def simulate_I_type(line, registers, Memory_address):
    imm_temp = line[0:12]
    imm = sign_extend(imm_temp, 12)
    rs1 = int(line[12:17], 2)
    func3 = line[17:20]
    rd = int(line[20:25], 2)
    opcode = line[25:32]
    # print(rd, rs1, imm, line)
    if (opcode == "0000011"):
        if (func3 == "010"):
            add = (registers[rs1] + imm) %overflow
            temp_str = format(add, '08X')
            if (Memory_address.get(f"0x{temp_str}") == None):
                if (temp_memory_address.get(add) == None):
                    return PC+4
                else:
                    if (rd != 0):
                        registers[rd] = temp_memory_address[add]
                    return PC+4
            else:
                if (rd != 0):
                    registers[rd] = Memory_address[f"0x{temp_str}"]
                return PC+4
        else:
            raise Exception("Unsupported I-type (func3)")
    elif (opcode == "0010011"):
        if (func3 == "000"):
            if (rd != 0):
                registers[rd] = (registers[rs1] + imm)%overflow
            return PC+4
        else:
            raise Exception("Unsupported I-type (func3)")
    elif (opcode == "1100111"):
        if (func3 == "000"):
        # print(rd, rs1, imm, line)
            if (rd != 0):
                registers[rd] = PC+4
            return (registers[rs1] + imm) %overflow
        else:
            raise Exception("Unsupported I-type")


def simulate_S_type(line, registers, Memory_address):
    imm_temp= line[0:7] + line[20:25]
    imm = sign_extend(imm_temp, 12)
    rs2 = int(line[7:12], 2)
    rs1 = int(line[12:17], 2)
    funct3 = line[17:20]
    opcode = line[25:32]
    # print(rs1, rs2, imm)
    if (opcode == "0100011" and funct3 == "010"):
        resulting_address = (registers[rs1] + imm) %overflow
        temp_str = format(resulting_address, '08X')
        if (Memory_address.get(f"0x{temp_str}") == None):
            temp_memory_address[resulting_address] = registers[rs2]
            return PC+4
        else:
            Memory_address[f"0x{temp_str}"] = registers[rs2]
            return PC+4
    else:
        raise Exception("Unsupported S-type")
    
def simulate_B_type(line, registers, Memory_address):
    imm_temp = line[0:1] + line[24:25] + line[1:7] + line[20:24] + '0'
    imm = sign_extend(imm_temp, 13)
    rs2 = int(line[7:12], 2)
    rs1 = int(line[12:17], 2)
    funct3 = line[17:20]
    # print(rs1 , rs2, imm)
    if (funct3 == "000"):
        if (registers[rs1] == registers[rs2] and imm == 0):
            return PC+4, True
        elif (registers[rs1] == registers[rs2]):
            return PC + imm, False
        else:
            return PC+4, False
    elif (funct3 == "001"):
        if (registers[rs1] != registers[rs2]):
            return PC+imm, False
        else:
            return PC+4, False
    else:
        raise Exception("Unsupported B-type")
    
def simulate_J_type(line, registers, Memory_address):
    imm_temp = line[12:20] + line[11:12] + line[1:11] + line[0:1]
    imm = sign_extend(imm_temp, 21)
    rd = int(line[20:25], 2)
    if rd != 0:
        registers[rd] = PC + 4
    return PC + imm

def load_instructions(filename):
    with open(filename, 'r') as f:
        lines = [line.strip() for line in f]
    return lines

def write_output(trace_array, output_file, temp):
    if (temp == 1):
        with open(output_file, 'w') as f:
            for line in trace_array:
                f.write(str(line) + " ")
            f.write("\n")
    else:
        with open(output_file, 'a') as f:
            for line in trace_array:
                f.write(str(line) + " ")
            f.write("\n")

def main():
    # if len(sys.argv) != 3:
    #     print("Usage: python Simulator.py <input_binary_file> <output_trace_file>")
    #     sys.exit(1)
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    #output_file = "new.txt"
    #input_file = "file.txt"
    output_decimal = output_file.replace(".txt", "_r.txt")
    lines = load_instructions(input_file)
    # registers, PC, data_memory = init_state()
    # run_simulation(instructions, registers, PC, data_memory, output_file)
    # lines = load_instructions("file.txt")
    init_memory_address(Memory_address)

    temp1 = 1

    while PC < 4*len(lines):
        if (PC//4 < 0):
            raise Exception("PC out of bounds")
        new_trace_array, trace_array, halt = type_of_instruction(lines[PC//4], Memory_address, registers)
        write_output(trace_array, output_file, temp1)
        write_output(new_trace_array, output_decimal, temp1)
        temp1 = 0
        if (halt):
            break
    if (halt is False):
        raise Exception("Halt not detected")
    # for line in lines:
    #     # print(line)
    #     # print(PC)
    #     type_of_instruction(line, Memory_address, registers)

    with open(output_file, 'a') as f:
        for i in Memory_address:
            f.write(i+":"+decimal_to_32bit(Memory_address[i]))
            f.write("\n")
    with open(output_decimal, 'a') as f:
        for i in Memory_address:
            f.write(str(i)+":"+str(Memory_address[i]))
            f.write("\n")
    # for i in Memory_address:
    #     print(i, end = '')
    #     print(':', end = '')
    #     print(decimal_to_32bit(Memory_address[i]))
    # print(sign_extend("1111111110000", 13))

if __name__ == "__main__":
    main()