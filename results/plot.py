import matplotlib.pyplot as plt

# this is how to get what we want, we'll adjust it when we decide what to do with the plots.
with open('test_results.txt', 'r') as f:
    lines = f.readlines()

nodes_5 = dict()
nodes_10 = dict()
for i in range(12):
    N = int(lines[i * 9 + 1].split()[2])
    difficulty = int(lines[i * 9 + 2].split()[2])
    capacity = int(lines[i * 9 + 3].split()[2])
    throughput = float(lines[i * 9 + 7].split()[2])
    mining_time = float(lines[i * 9 + 8].split()[5])
    if i < 6:
        nodes_5[str((difficulty, capacity))] = (throughput, mining_time)
    else:
        nodes_10[str((difficulty, capacity))] = (throughput, mining_time)

plt.figure(1)
plt.plot(list(nodes_5.keys()), list(zip(*nodes_5.values()))[0], 'mo-', label='#nodes = 5')
plt.plot(list(nodes_10.keys()), list(zip(*nodes_10.values()))[0], 'co-', label='#nodes = 10')
plt.title('System Throughput')
plt.ylabel('Throughput (transactions/s)')
plt.xlabel('(Difficulty, Capacity)')
plt.legend()
plt.savefig('throughput.png')

plt.figure(2)
plt.plot(list(nodes_5.keys()), list(zip(*nodes_5.values()))[1], 'mo-', label='#nodes = 5')
plt.plot(list(nodes_10.keys()), list(zip(*nodes_10.values()))[1], 'co-', label='#nodes = 10')
plt.title('Mean time for new block')
plt.ylabel('Mean time (s)')
plt.xlabel('(Difficulty, Capacity)')
plt.legend()
plt.savefig('mean_time.png')