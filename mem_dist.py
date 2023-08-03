import sys 
import matplotlib.pyplot as plt

def parseline(f):
    return [int(x) for x in f.readline().split()]

def size_text(num_bytes):
    size_name = ['B', 'K', 'M', 'G']
    size_idx = 0
    ret = num_bytes
    while ret >= 1024:
        size_idx += 1
        ret /= 1024
    return f'{round(ret)}{size_name[size_idx]}'

if len(sys.argv) != 4:
    print('usage: python mem_dist.py in.graph in.svg out.svg')
    exit(1)
graph_input = sys.argv[1]
svg_input = sys.argv[2]
svg_output = sys.argv[3]

with open(graph_input) as f:
    num_inputs, = parseline(f)
    inputs = parseline(f)
    assert(len(inputs) == num_inputs)
    print(inputs)

    num_outputs, = parseline(f)
    outputs = parseline(f)
    assert(len(outputs) == num_outputs)
    print(outputs)

    num_tensors, = parseline(f)
    tensors = []
    for _ in range(num_tensors):
        size, buf_idx = parseline(f)
        tensors.append((size, buf_idx))
    print(tensors)

    num_ops, = parseline(f)
    ops = []
    for _ in range(num_ops):
        num_op_inputs, = parseline(f)
        op_inputs = parseline(f)
        assert(len(op_inputs) == num_op_inputs)
        num_op_outputs, = parseline(f)
        op_outputs = parseline(f)
        assert(len(op_outputs) == num_op_outputs)
        ops.append((op_inputs, op_outputs))
    print(ops)

    num_buffers, = parseline(f)
    buffers = []
    for _ in range(num_buffers):
        buffer_size, = parseline(f)
        buffers.append(buffer_size)
    print(buffers)

output_to_op = {}
for idx, (_, op_outputs) in enumerate(ops):
    for op_output in op_outputs:
        assert(op_output != -1)
        assert(op_output not in output_to_op)
        output_to_op[op_output] = idx
print(output_to_op)

for op_inputs, _ in ops:
    for op_input in op_inputs:
        if op_input == -1:
            continue
        buffer_size, buffer_idx = tensors[op_input]
        if (op_input in output_to_op) or (op_input in inputs):
            assert(buffers[buffer_idx] == -1)
        else:
            assert(buffers[buffer_idx] == buffer_size)

graph = [[] for _ in range(num_ops)]
for op_idx, (op_inputs, _) in enumerate(ops):
    for op_input in op_inputs:
        if op_input == -1:
            continue
        if op_input in output_to_op:
            graph[output_to_op[op_input]].append((op_idx, op_input))
print(graph)

rev_graph = [[] for _ in range(num_ops)]
for op_idx, nexts in enumerate(graph):
    for next_op_idx, next_op_tensor in nexts:
        rev_graph[next_op_idx].append((op_idx, next_op_tensor))
print(rev_graph)

''' check validity of execution order
G = nx.DiGraph()
for idx, next_list in enumerate(graph):
    G.add_node(idx)
    for next, _ in next_list:
        G.add_edge(idx, next)
if list(range(num_ops)) in list(nx.all_topological_sorts(G)):
    print("inside")

requirements = {i: set() for i in range(num_ops)}
for idx, nexts in enumerate(graph):
    for next, _ in nexts:
        requirements[next].add(idx)
print(requirements)

visited = set()
order = list(range(num_ops))
for x in order:
    for requirement in requirements[x]:
        if requirement not in visited:
            assert(False)
    visited.add(x)
'''

retaining = {}
for op_idx, (op_inputs, op_outputs) in enumerate(ops):
    for op_input in op_inputs:
        if op_input in inputs:
            rev_graph[op_idx].append((-1, op_input))
            if op_input in retaining:
                retaining[op_input] += 1
            else:
                retaining[op_input] = 1
    for op_output in op_outputs:
        if op_output in outputs:
            graph[op_idx].append((-1, op_output))
print(retaining)

mem = {}
for op_idx in range(num_ops):
    for _, tensor_idx in graph[op_idx]:
        if tensor_idx in retaining:
            retaining[tensor_idx] += 1
        else:
            retaining[tensor_idx] = 1

    mem_sum = 0
    for retaining_idx in retaining.keys():
        mem_sum += tensors[retaining_idx][0]
    mem[op_idx] = mem_sum

    for _, tensor_idx in rev_graph[op_idx]:
        assert(tensor_idx in retaining)
        if retaining[tensor_idx] == 1:
            del retaining[tensor_idx]
        else:
            retaining[tensor_idx] -= 1
print(mem)

for x in retaining.keys():
    assert(x in outputs)

with open(svg_input) as f:
    svg = f.read()
for op_idx in range(num_ops):
    end = svg.find('</text>', svg.find(f'node-id-{op_idx}'))
    start = svg.rfind('>', 0, end)
    orig = svg[start + 1: end]
    new = size_text(mem[op_idx])
    middle = f' onmouseover="this.innerHTML=\'{orig}\'" onmouseout="this.innerHTML=\'{new}\'">{new}'
    svg = svg[:start] + middle + svg[end:]
with open(svg_output, 'w') as f:
    f.write(svg)

plt.bar(mem.keys(), mem.values())
plt.show()