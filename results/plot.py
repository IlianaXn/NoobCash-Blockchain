
# this is how to get what we want, we'll adjust it when we decide what to do with the plots.
with open('test_results.txt', 'r') as f:
    lines = f.readlines()

for i in range(12):
    N = int(lines[i * 9 + 1].split()[2])
    difficulty = int(lines[i * 9 + 2].split()[2])
    capacity = int(lines[i * 9 + 3].split()[2])
    throughput = float(lines[i * 9 + 3].split()[2])
    mining_time = float(lines[i * 9 + 4].split()[5])