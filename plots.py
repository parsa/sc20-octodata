#!/usr/bin/env python
# coding: utf-8

import re
import numpy as np
import pandas as pd
import matplotlib
import matplotlib.ticker as ticker
import matplotlib.pyplot as plt
import zipfile


def percent_formatter(y, position):
    # Ignore the passed in position. This has the effect of scaling the default
    # tick locations.
    s = str(100 * y)

    # The percent symbol needs escaping in latex
    if matplotlib.rcParams['text.usetex'] is True:
        return s + r'$\%$'
    else:
        return s + '%'


PercentFormatter = ticker.FuncFormatter(percent_formatter)


# Performance Counter Parsing RegEx

locality_regex = re.compile(r'/agas\{locality#(\d+)[^}]*\}')


pfx_counter_regex = re.compile(
    r'/([a-z_]+){locality#(\d+)/total}/(?:(?:(count|time)/)'
    '([a-z/_-]+)|([a-z/_-]+)/(?:(count|time))),([0-9]+),'
    r'([0-9.]+),\[[a-z]+\],([0-9.\+e]+)(?:,\[([a-z]+)?\])?'
)


# Read the Data Files


dataset = []

with zipfile.ZipFile('data.zip', 'r') as arxiv:
    for fn in arxiv.namelist():
        if fn.endswith('.out'):
            content = arxiv.read(fn).decode('utf-8')
            content = arxiv.read(fn).decode('utf-8')
            localities = set(int(x) for x in locality_regex.findall(content))
            if (localities):
                print('Processing "%s"...' % fn)
            else:
                print('No data found in "%s". Skipping...' % fn)
                continue
            node_count = max(localities) + 1

            for m in pfx_counter_regex.finditer(content):
                is_rev = m.group(3) is not None

                dataset.append({
                    'sys': m.group(1),
                    'proc': (m.group(4) if is_rev else m.group(5)).replace('/', '.'),
                    'type': m.group(3) if is_rev else m.group(6),
                    'locality': int(m.group(2)),
                    'value': float(m.group(9)),
                    'value_unit': m.group(10),
                    'timestamp': float(m.group(8)),
                    'iteration': int(m.group(7)),
                    'nodes': node_count,
                })

df = pd.DataFrame(dataset)


# import tarfile
#
# dataset = []
#
# with tarfile.open('cori-17mar17.tar.bz2', mode='r:bz2') as arxiv:
#     for i in arxiv.getnames():
#         if i.endswith('.txt'):
#             n_nodes = int(i.split('.')[0])
#             fd = arxiv.extractfile(i)
#             for m in pfx_pattern.finditer(fd.read()):
#                 is_rev = m.group(3) != None
#
#                 dataset.append({
#                     'sys': m.group(1),
#                     'proc': (m.group(4) if is_rev else m.group(5)).replace('/', '.'),
#                     'type': m.group(3) if is_rev else m.group(6),
#                     'locality': int(m.group(2)),
#                     'value': float(m.group(9)),
#                     'value_unit': m.group(10),
#                     'timestamp': m.group(8),
#                     'iteration': int(m.group(7)),
#                     'nodes': n_nodes,
#                 })
#
# df = pd.DataFrame(dataset)

# Last Iteration

d = None
for i, j in df[['nodes', 'iteration']].groupby(
        'nodes').max().iteration.to_dict().items():
    x = df[(df.nodes == i) & (df.iteration == j)]
    if d is None:
        d = x
    else:
        d = pd.concat([d, x])


print(d[(d.sys == 'agas') & (d.type == 'count')].proc.unique())
print(d[(d.sys == 'agas') & (d.type == 'time')].proc.unique())


# ---

# Total

a = []
for i in range(0, 11):
    a += [1e-9 * d[(d.sys == 'agas') & (d.nodes == 2**i) & (d.type == 'time') &
                   (d.locality != 0) & (d.locality != 0)].value.sum() / ((2 ** i - 1) * 24 * 362)]

plt.figure(figsize=(8, 5))
plt.plot([2**i for i in range(0, 11)], a, c='b')
plt.grid()

plt.title('All AGAS Services - Portion of CPU Time - Level 12')
plt.xlabel('Number of Nodes')
plt.ylabel('Percentage of CPU Time spent in Calls')

plt.gca().yaxis.set_major_formatter(ticker.PercentFormatter(1))
plt.gca().xaxis.set_major_locator(
    ticker.FixedLocator([2, 32, 64, 128, 256, 512, 1024]))
plt.gca().set_xlim(left=0., right=512)
plt.gca().set_ylim(bottom=0., top=.002)

plt.savefig('octotiger_total_time.pdf')


# GIDs

# Bind GID

crt = d[(d.sys == 'agas') & (d.proc == 'bind_gid') & (d.type == 'count')]

plt.figure(figsize=(13, 10))
plt.scatter(crt.nodes, crt.value, c='r', alpha=.3)
#
t = crt[crt.locality == 0]
plt.plot(t.nodes, t.value, label='Locality 0')
#
t = crt[crt.locality == 1]
plt.plot(t.nodes, t.value, label='Locality 1')
#
t = crt.groupby('nodes', as_index=False).last()
plt.plot(t.nodes, t.value, label='Locality $n - 1$')
#
plt.grid()

plt.legend(loc='upper center', bbox_to_anchor=(
    0.5, -0.05), fancybox=True, shadow=True, ncol=5)
plt.title('Bind GID - Count')
plt.xlabel('Number of Nodes')
plt.ylabel('Number of Calls')

plt.gca().xaxis.set_major_locator(ticker.LogLocator(base=2))
plt.gca().set_xlim(left=0.)
plt.gca().set_ylim(bottom=0.)


crt = d[(d.sys == 'agas') & (d.proc == 'bind_gid') & (d.type == 'time')]
t = (1e-9 * crt.value / crt.timestamp) / 24.

plt.figure(figsize=(8, 5))
plt.scatter(crt.nodes, t, c='0', alpha=.5)

og = crt.sort_values(
    by='value',
    ascending=False).groupby(
        'nodes',
    as_index=False)
y1 = (1e-9 * og.first().value / og.first().timestamp) / 24.
y2 = (1e-9 * og.last().value / og.last().timestamp) / 24.
#plt.fill_between(crt.nodes, t, facecolor='r', alpha=.1)
plt.fill_between(
    og.groups.keys(),
    y1,
    y2,
    label='Other Localities',
    alpha=.1,
    color='0')

plt.grid()

#plt.legend(loc='upper center', bbox_to_anchor=(0.5, -0.05), fancybox=True, shadow=True, ncol=5)
plt.title('Bind GID - Portion of CPU Time')
plt.xlabel('Number of Nodes')
plt.ylabel('Percentage of CPU Time spent in Calls')

plt.gca().yaxis.set_major_formatter(ticker.PercentFormatter(1))
plt.gca().xaxis.set_major_locator(
    ticker.FixedLocator([2, 32, 64, 128, 256, 512, 1024]))
plt.gca().set_xlim(left=0.)
plt.gca().set_ylim(bottom=0., top=.00002)

plt.savefig('octotiger_bind_gid_time.pdf')


crt = d[(d.sys == 'agas') & (d.proc == 'bind_gid') & (d.type == 'time')]

plt.figure(figsize=(13, 10))
plt.scatter(crt.nodes, crt.value, c='r', alpha=.3)
#
t = crt[crt.locality == 0]
plt.plot(t.nodes, t.value, label='Locality 0')
#
t = crt[crt.locality == 1]
plt.plot(t.nodes, t.value, label='Locality 1')
#
t = crt.groupby('nodes', as_index=False).last()
plt.plot(t.nodes, t.value, label='Locality $n - 1$')
#
plt.grid()

plt.legend(loc='upper center', bbox_to_anchor=(
    0.5, -0.05), fancybox=True, shadow=True, ncol=5)
plt.title('Bind GID - Time')
plt.xlabel('Number of Nodes')
plt.ylabel('Duration of Calls')

plt.gca().xaxis.set_major_locator(ticker.LogLocator(base=2))
plt.gca().set_xlim(left=0.)
plt.gca().set_ylim(bottom=0., top=2e6)


# Unbind GID

crt = d[(d.sys == 'agas') & (d.proc == 'unbind_gid') & (d.type == 'count')]

plt.figure(figsize=(13, 10))
plt.scatter(crt.nodes, crt.value, c='r', alpha=.1)
#
t = crt[crt.locality == 0]
plt.plot(t.nodes, t.value, label='Locality 0')
#
t = crt[crt.locality == 1]
plt.plot(t.nodes, t.value, label='Locality 1')
#
t = crt.groupby('nodes', as_index=False).last()
plt.plot(t.nodes, t.value, label='Locality $n - 1$')
#
plt.grid()

plt.legend(loc='upper center', bbox_to_anchor=(
    0.5, -0.05), fancybox=True, shadow=True, ncol=5)
plt.title('Unbind GID - Count')
plt.xlabel('Number of Nodes')
plt.ylabel('Number of Calls')

plt.gca().xaxis.set_major_locator(ticker.LogLocator(base=2))
plt.gca().set_xlim(left=0.)
plt.gca().set_ylim(bottom=0.)


# Resolve GID

crt = d[(d.sys == 'agas') & (d.proc == 'resolve_gid') & (d.type == 'count')]

plt.figure(figsize=(13, 10))
plt.scatter(crt.nodes, crt.value, c='r', alpha=.3)
#
t = crt[crt.locality == 0]
plt.plot(t.nodes, t.value, label='Locality 0')
#
t = crt[crt.locality == 1]
plt.plot(t.nodes, t.value, label='Locality 1')
#
t = crt.groupby('nodes', as_index=False).last()
plt.plot(t.nodes, t.value, label='Locality $n - 1$')
#
plt.grid()

plt.legend(loc='upper center', bbox_to_anchor=(
    0.5, -0.05), fancybox=True, shadow=True, ncol=5)
plt.title('Resolve GID - Count')
plt.xlabel('Number of Nodes')
plt.ylabel('Number of Calls')

plt.gca().xaxis.set_major_locator(ticker.LogLocator(base=2))
plt.gca().set_xlim(left=0.)
plt.gca().set_ylim(bottom=0.)


crt[(crt.nodes == 1)]


crt = d[(d.sys == 'agas') & (d.proc == 'resolve_gid') & (d.type == 'time')]
t = (1e-9 * crt.value / crt.timestamp) / 24.

plt.figure(figsize=(8, 5))
plt.scatter(crt.nodes, t, c='0', alpha=.5)

og = crt.sort_values(
    by='value',
    ascending=False).groupby(
        'nodes',
    as_index=False)
y1 = (1e-9 * og.first().value / og.first().timestamp) / 24.
y2 = (1e-9 * og.last().value / og.last().timestamp) / 24.
plt.fill_between(
    og.groups.keys(),
    y1,
    y2,
    label='Other Localities',
    alpha=.1,
    color='0')
#
plt.grid()

plt.title('Resolve GID - Portion of CPU Time')
plt.xlabel('Number of Nodes')
plt.ylabel('Percentage of CPU Time spent in Calls')

plt.gca().yaxis.set_major_formatter(ticker.PercentFormatter(1))
plt.gca().xaxis.set_major_locator(
    ticker.FixedLocator([2, 32, 64, 128, 256, 512, 1024]))
plt.gca().set_xlim(left=0.)
plt.gca().set_ylim(bottom=0., top=.0014)
plt.savefig('octotiger_resolve_gid_time.pdf', format='pdf')


# ---

# Garbage Collection

# Increment Credit

crt = d[(d.sys == 'agas') & (d.proc == 'increment_credit') & (d.type == 'count')]

plt.figure(figsize=(13, 10))
plt.scatter(crt.nodes, crt.value, c='r', alpha=.3)
#
t = crt[crt.locality == 0]
plt.plot(t.nodes, t.value, label='Locality 0')
#
t = crt[crt.locality == 1]
plt.plot(t.nodes, t.value, label='Locality 1')
#
t = crt.groupby('nodes', as_index=False).last()
plt.plot(t.nodes, t.value, label='Locality $n - 1$')
#
plt.grid()

plt.legend(loc='upper center', bbox_to_anchor=(
    0.5, -0.05), fancybox=True, shadow=True, ncol=5)
plt.title('Increment Credit - Count')
plt.xlabel('Number of Nodes')
plt.ylabel('Number of Calls')

plt.gca().xaxis.set_major_locator(ticker.LogLocator(base=2))
plt.gca().set_xlim(left=0.)
plt.gca().set_ylim(bottom=0.)


crt = d[(d.sys == 'agas') & (d.proc == 'increment_credit') & (d.type == 'time')]

plt.figure(figsize=(13, 10))
plt.scatter(crt.nodes, crt.value, c='r', alpha=.3)
#
t = crt[crt.locality == 0]
plt.plot(t.nodes, t.value, label='Locality 0')
#
t = crt[crt.locality == 1]
plt.plot(t.nodes, t.value, label='Locality 1')
#
t = crt.groupby('nodes', as_index=False).last()
plt.plot(t.nodes, t.value, label='Locality $n - 1$')
#
plt.grid()

plt.legend(loc='upper center', bbox_to_anchor=(
    0.5, -0.05), fancybox=True, shadow=True, ncol=5)
plt.title('Increment Credit - Time')
plt.xlabel('Number of Nodes')
plt.ylabel('Duration of Calls')

plt.gca().xaxis.set_major_locator(ticker.LogLocator(base=2))
plt.gca().set_xlim(left=0.)
plt.gca().set_ylim(bottom=0.)


# Decrement Credit

crt = d[(d.sys == 'agas') & (d.proc == 'decrement_credit') & (d.type == 'count')]

plt.figure(figsize=(13, 10))
plt.scatter(crt.nodes, crt.value, c='r', alpha=.3)
#
t = crt[crt.locality == 0]
plt.plot(t.nodes, t.value, label='Locality 0')
#
t = crt[crt.locality == 1]
plt.plot(t.nodes, t.value, label='Locality 1')
#
t = crt.groupby('nodes', as_index=False).last()
plt.plot(t.nodes, t.value, label='Locality $n - 1$')
#
plt.grid()

plt.legend(loc='upper center', bbox_to_anchor=(
    0.5, -0.05), fancybox=True, shadow=True, ncol=5)
plt.title('Decrement Credit - Count')
plt.xlabel('Number of Nodes')
plt.ylabel('Number of Calls')

plt.gca().xaxis.set_major_locator(ticker.LogLocator(base=2))
plt.gca().set_xlim(left=0.)
plt.gca().set_ylim(bottom=0.)


crt = d[(d.sys == 'agas') & (d.proc == 'decrement_credit') & (d.type == 'time')]
t = (1e-9 * crt.value / crt.timestamp) / 24.

plt.figure(figsize=(8, 5))
plt.scatter(crt.nodes, t, c='0', alpha=.5)

og = crt.sort_values(
    by='value',
    ascending=False).groupby(
        'nodes',
    as_index=False)
y1 = (1e-9 * og.first().value / og.first().timestamp) / 24.
y2 = (1e-9 * og.last().value / og.last().timestamp) / 24.
plt.fill_between(
    og.groups.keys(),
    y1,
    y2,
    label='Other Localities',
    alpha=.1,
    color='0')
#
plt.grid()

plt.title('Decrement Credit - Portion of CPU Time')
plt.xlabel('Number of Nodes')
plt.ylabel('Percentage of CPU Time spent in Calls')

plt.gca().yaxis.set_major_formatter(ticker.PercentFormatter(1))
plt.gca().xaxis.set_major_locator(
    ticker.FixedLocator([2, 32, 64, 128, 256, 512, 1024]))
plt.gca().set_xlim(left=0.)
plt.gca().set_ylim(bottom=0., top=0.0005)

plt.savefig('octotiger_decrement_credit_time.pdf')


# ---

# Locality Namespace

# Route

crt = d[(d.sys == 'agas') & (d.proc == 'route') & (d.type == 'count')]

plt.figure(figsize=(13, 10))
plt.scatter(crt.nodes, crt.value, c='r', alpha=.3)
#
t = crt[crt.locality == 0]
plt.plot(t.nodes, t.value, label='Locality 0')
#
t = crt[crt.locality == 1]
plt.plot(t.nodes, t.value, label='Locality 1')
#
t = crt.groupby('nodes', as_index=False).last()
plt.plot(t.nodes, t.value, label='Locality $n - 1$')
#
plt.grid()

plt.legend(loc='upper center', bbox_to_anchor=(
    0.5, -0.05), fancybox=True, shadow=True, ncol=5)
plt.title('Route - Count')
plt.xlabel('Number of Nodes')
plt.ylabel('Number of Calls')

plt.gca().xaxis.set_major_locator(ticker.LogLocator(base=2))
plt.gca().set_xlim(left=0.)
plt.gca().set_ylim(bottom=0.)


for i, j in enumerate(crt[crt.locality == 0].value):
    print(i, int(j), hex(int(j)))


# Exclude locality 0 measurements for route time. The measurements are
# obviously wrong.

crt = d[(d.sys == 'agas') & (d.proc == 'route') &
        (d.type == 'time') & (d.locality != 0)]
t = (1e-9 * crt.value / crt.timestamp) / 24.

plt.figure(figsize=(8, 5))
plt.scatter(crt.nodes, t, c='0', alpha=.3)

og = crt.sort_values(
    by='value',
    ascending=False).groupby(
        'nodes',
    as_index=False)
y1 = (1e-9 * og.first().value / og.first().timestamp) / 24.
y2 = (1e-9 * og.last().value / og.last().timestamp) / 24.
plt.fill_between(
    og.groups.keys(),
    y1,
    y2,
    label='Other Localities',
    alpha=.1,
    color='0')
#
#t = crt[crt.locality==0]
#plt.plot(t.nodes, (1e-9 * t.value / t.timestamp) / 24., label='Locality 0')
#
plt.grid()

#plt.legend(loc='upper center', bbox_to_anchor=(0.5, -0.05), fancybox=True, shadow=True, ncol=5)
plt.title('Route - Portion of CPU Time')
plt.xlabel('Number of Nodes')
plt.ylabel('Percentage of CPU Time spent in Calls')

plt.gca().yaxis.set_major_formatter(ticker.PercentFormatter(1))
plt.gca().xaxis.set_major_locator(
    ticker.FixedLocator([2, 32, 64, 128, 256, 512, 1024]))
plt.gca().set_xlim(left=0.)
plt.gca().set_ylim(bottom=0., top=.00005)

plt.savefig('octotiger_route_time.pdf')


# Allocate

crt = d[(d.sys == 'agas') & (d.proc == 'allocate') & (d.type == 'count')]

plt.figure(figsize=(13, 10))
plt.scatter(crt.nodes, crt.value, c='r', alpha=.3)
#
t = crt[crt.locality == 0]
plt.plot(t.nodes, t.value, label='Locality 0')
#
t = crt[crt.locality == 1]
plt.plot(t.nodes, t.value, label='Locality 1')
#
t = crt.groupby('nodes', as_index=False).last()
plt.plot(t.nodes, t.value, label='Locality $n - 1$')
#
plt.grid()

plt.legend(loc='upper center', bbox_to_anchor=(
    0.5, -0.05), fancybox=True, shadow=True, ncol=5)
plt.title('Allocate - Count')
plt.xlabel('Number of Nodes')
plt.ylabel('Number of Calls')

plt.gca().xaxis.set_major_locator(ticker.LogLocator(base=2))
plt.gca().set_xlim(left=0.)
plt.gca().set_ylim(bottom=0.)


crt = d[(d.sys == 'agas') & (d.proc == 'allocate') & (d.type == 'time')]

plt.figure(figsize=(13, 10))
plt.scatter(crt.nodes, crt.value, c='r', alpha=.3)
#
t = crt[crt.locality == 0]
plt.plot(t.nodes, t.value, label='Locality 0')
#
t = crt[crt.locality == 1]
plt.plot(t.nodes, t.value, label='Locality 1')
#
t = crt.groupby('nodes', as_index=False).last()
plt.plot(t.nodes, t.value, label='Locality $n - 1$')
#
plt.grid()

plt.legend(loc='upper center', bbox_to_anchor=(
    0.5, -0.05), fancybox=True, shadow=True, ncol=5)
plt.title('Allocate - Time')
plt.xlabel('Number of Nodes')
plt.ylabel('Duration of Calls')

plt.gca().xaxis.set_major_locator(ticker.LogLocator(base=2))
plt.gca().set_xlim(left=0.)
plt.gca().set_ylim(bottom=0.)


# Migration

# Begin Migration

crt = d[(d.sys == 'agas') & (d.proc == 'begin_migration') & (d.type == 'count')]

plt.figure(figsize=(13, 10))
plt.scatter(crt.nodes, crt.value, c='r', alpha=.3)
#
t = crt[crt.locality == 0]
plt.plot(t.nodes, t.value, label='Locality 0')
#
t = crt[crt.locality == 1]
plt.plot(t.nodes, t.value, label='Locality 1')
#
t = crt.groupby('nodes', as_index=False).last()
plt.plot(t.nodes, t.value, label='Locality $n - 1$')
#
plt.grid()

plt.legend(loc='upper center', bbox_to_anchor=(
    0.5, -0.05), fancybox=True, shadow=True, ncol=5)
plt.title('Begin Migration - Count')
plt.xlabel('Number of Nodes')
plt.ylabel('Number of Calls')

plt.gca().xaxis.set_major_locator(ticker.LogLocator(base=2))
plt.gca().set_xlim(left=0.)
plt.gca().set_ylim(bottom=0.)


crt = d[(d.sys == 'agas') & (d.proc == 'begin_migration') & (d.type == 'time')]

plt.figure(figsize=(13, 10))
plt.scatter(crt.nodes, crt.value, c='r', alpha=.3)
#
t = crt[crt.locality == 0]
plt.plot(t.nodes, t.value, label='Locality 0')
#
t = crt[crt.locality == 1]
plt.plot(t.nodes, t.value, label='Locality 1')
#
t = crt.groupby('nodes', as_index=False).last()
plt.plot(t.nodes, t.value, label='Locality $n - 1$')
#
plt.grid()

plt.legend(loc='upper center', bbox_to_anchor=(
    0.5, -0.05), fancybox=True, shadow=True, ncol=5)
plt.title('Begin Migration - Time')
plt.xlabel('Number of Nodes')
plt.ylabel('Duration of Calls')

plt.gca().xaxis.set_major_locator(ticker.LogLocator(base=2))
plt.gca().set_xlim(left=0.)
plt.gca().set_ylim(bottom=0.)


# End Migration

crt = d[(d.sys == 'agas') & (d.proc == 'end_migration') & (d.type == 'count')]

plt.figure(figsize=(13, 10))
plt.scatter(crt.nodes, crt.value, c='r', alpha=.3)
#
t = crt[crt.locality == 0]
plt.plot(t.nodes, t.value, label='Locality 0')
#
t = crt[crt.locality == 1]
plt.plot(t.nodes, t.value, label='Locality 1')
#
t = crt.groupby('nodes', as_index=False).last()
plt.plot(t.nodes, t.value, label='Locality $n - 1$')
#
plt.grid()

plt.legend(loc='upper center', bbox_to_anchor=(
    0.5, -0.05), fancybox=True, shadow=True, ncol=5)
plt.title('End Migration - Count')
plt.xlabel('Number of Nodes')
plt.ylabel('Number of Calls')

plt.gca().xaxis.set_major_locator(ticker.LogLocator(base=2))
plt.gca().set_xlim(left=0.)
plt.gca().set_ylim(bottom=0.)


crt = d[(d.sys == 'agas') & (d.proc == 'end_migration') & (d.type == 'time')]

plt.figure(figsize=(13, 10))
plt.scatter(crt.nodes, crt.value, c='r', alpha=.3)
#
t = crt[crt.locality == 0]
plt.plot(t.nodes, t.value, label='Locality 0')
#
t = crt[crt.locality == 1]
plt.plot(t.nodes, t.value, label='Locality 1')
#
t = crt.groupby('nodes', as_index=False).last()
plt.plot(t.nodes, t.value, label='Locality $n - 1$')
#
plt.grid()

plt.legend(loc='upper center', bbox_to_anchor=(
    0.5, -0.05), fancybox=True, shadow=True, ncol=5)
plt.title('End Migration - Time')
plt.xlabel('Number of Nodes')
plt.ylabel('Duration of Calls')

plt.gca().xaxis.set_major_locator(ticker.LogLocator(base=2))
plt.gca().set_xlim(left=0.)
plt.gca().set_ylim(bottom=0.)


# Component Namespace

# Bind Prefix

crt = d[(d.sys == 'agas') & (d.proc == 'bind_prefix') & (d.type == 'count')]

plt.figure(figsize=(13, 10))
plt.scatter(crt.nodes, crt.value, c='r', alpha=.3)
#
t = crt[crt.locality == 0]
plt.plot(t.nodes, t.value, label='Locality 0')
#
t = crt[crt.locality == 1]
plt.plot(t.nodes, t.value, label='Locality 1')
#
t = crt.groupby('nodes', as_index=False).last()
plt.plot(t.nodes, t.value, label='Locality $n - 1$')
#
plt.grid()

plt.legend(loc='upper center', bbox_to_anchor=(
    0.5, -0.05), fancybox=True, shadow=True, ncol=5)
plt.title('Bind Prefix - Count')
plt.xlabel('Number of Nodes')
plt.ylabel('Number of Calls')

plt.gca().xaxis.set_major_locator(ticker.LogLocator(base=2))
plt.gca().set_xlim(left=0.)
plt.gca().set_ylim(bottom=0.)


crt = d[(d.sys == 'agas') & (d.proc == 'bind_prefix') & (d.type == 'time')]

plt.figure(figsize=(13, 10))
plt.scatter(crt.nodes, crt.value, c='r', alpha=.3)
#
t = crt[crt.locality == 0]
plt.plot(t.nodes, t.value, label='Locality 0')
#
t = crt[crt.locality == 1]
plt.plot(t.nodes, t.value, label='Locality 1')
#
t = crt.groupby('nodes', as_index=False).last()
plt.plot(t.nodes, t.value, label='Locality $n - 1$')
#
plt.grid()

plt.legend(loc='upper center', bbox_to_anchor=(
    0.5, -0.05), fancybox=True, shadow=True, ncol=5)
plt.title('Bind Prefix - Time')
plt.xlabel('Number of Nodes')
plt.ylabel('Duration of Calls')

plt.gca().xaxis.set_major_locator(ticker.LogLocator(base=2))
plt.gca().set_xlim(left=0.)
plt.gca().set_ylim(bottom=0.)


# Bind Name

crt = d[(d.sys == 'agas') & (d.proc == 'bind_name') & (d.type == 'count')]

plt.figure(figsize=(13, 10))
plt.scatter(crt.nodes, crt.value, c='r', alpha=.3)
#
t = crt[crt.locality == 0]
plt.plot(t.nodes, t.value, label='Locality 0')
#
t = crt[crt.locality == 1]
plt.plot(t.nodes, t.value, label='Locality 1')
#
t = crt.groupby('nodes', as_index=False).last()
plt.plot(t.nodes, t.value, label='Locality $n - 1$')
#
plt.grid()

plt.legend(loc='upper center', bbox_to_anchor=(
    0.5, -0.05), fancybox=True, shadow=True, ncol=5)
plt.title('Bind Name - Count')
plt.xlabel('Number of Nodes')
plt.ylabel('Number of Calls')

plt.gca().xaxis.set_major_locator(ticker.LogLocator(base=2))
plt.gca().set_xlim(left=0.)
plt.gca().set_ylim(bottom=0.)


crt = d[(d.sys == 'agas') & (d.proc == 'bind_name') & (d.type == 'time')]

plt.figure(figsize=(13, 10))
plt.scatter(crt.nodes, crt.value, c='r', alpha=.3)
#
t = crt[crt.locality == 0]
plt.plot(t.nodes, t.value, label='Locality 0')
#
t = crt[crt.locality == 1]
plt.plot(t.nodes, t.value, label='Locality 1')
#
t = crt.groupby('nodes', as_index=False).last()
plt.plot(t.nodes, t.value, label='Locality $n - 1$')
#
plt.grid()

plt.legend(loc='upper center', bbox_to_anchor=(
    0.5, -0.05), fancybox=True, shadow=True, ncol=5)
plt.title('Bind Name - Time')
plt.xlabel('Number of Nodes')
plt.ylabel('Duration of Calls')

plt.gca().xaxis.set_major_locator(ticker.LogLocator(base=2))
plt.gca().set_xlim(left=0.)
plt.gca().set_ylim(bottom=0.)


# Unbind Name

crt = d[(d.sys == 'agas') & (d.proc == 'unbind_name') & (d.type == 'count')]

plt.figure(figsize=(13, 10))
plt.scatter(crt.nodes, crt.value, c='r', alpha=.3)
#
t = crt[crt.locality == 0]
plt.plot(t.nodes, t.value, label='Locality 0')
#
t = crt[crt.locality == 1]
plt.plot(t.nodes, t.value, label='Locality 1')
#
t = crt.groupby('nodes', as_index=False).last()
plt.plot(t.nodes, t.value, label='Locality $n - 1$')
#
plt.grid()

plt.legend(loc='upper center', bbox_to_anchor=(
    0.5, -0.05), fancybox=True, shadow=True, ncol=5)
plt.title('Unbind Name - Count')
plt.xlabel('Number of Nodes')
plt.ylabel('Number of Calls')

plt.gca().xaxis.set_major_locator(ticker.LogLocator(base=2))
plt.gca().set_xlim(left=0.)
plt.gca().set_ylim(bottom=0.)


crt = d[(d.sys == 'agas') & (d.proc == 'unbind_name') & (d.type == 'time')]

plt.figure(figsize=(13, 10))
plt.scatter(crt.nodes, crt.value, c='r', alpha=.3)
#
t = crt[crt.locality == 0]
plt.plot(t.nodes, t.value, label='Locality 0')
#
t = crt[crt.locality == 1]
plt.plot(t.nodes, t.value, label='Locality 1')
#
t = crt.groupby('nodes', as_index=False).last()
plt.plot(t.nodes, t.value, label='Locality $n - 1$')
#
plt.grid()

plt.legend(loc='upper center', bbox_to_anchor=(
    0.5, -0.05), fancybox=True, shadow=True, ncol=5)
plt.title('Unbind Name - Time')
plt.xlabel('Number of Nodes')
plt.ylabel('Duration of Calls')

plt.gca().xaxis.set_major_locator(ticker.LogLocator(base=2))
plt.gca().set_xlim(left=0.)
plt.gca().set_ylim(bottom=0.)


# Resolve ID

crt = d[(d.sys == 'agas') & (d.proc == 'resolve_id') & (d.type == 'count')]

plt.figure(figsize=(13, 10))
plt.scatter(crt.nodes, crt.value, c='r', alpha=.3)
#
t = crt[crt.locality == 0]
plt.plot(t.nodes, t.value, label='Locality 0')
#
t = crt[crt.locality == 1]
plt.plot(t.nodes, t.value, label='Locality 1')
#
t = crt.groupby('nodes', as_index=False).last()
plt.plot(t.nodes, t.value, label='Locality $n - 1$')
#
plt.grid()

plt.legend(loc='upper center', bbox_to_anchor=(
    0.5, -0.05), fancybox=True, shadow=True, ncol=5)
plt.title('Resolve ID - Count')
plt.xlabel('Number of Nodes')
plt.ylabel('Number of Calls')

plt.gca().xaxis.set_major_locator(ticker.LogLocator(base=2))
plt.gca().set_xlim(left=0.)
plt.gca().set_ylim(bottom=0.)


crt = d[(d.sys == 'agas') & (d.proc == 'resolve_id') & (d.type == 'time')]

plt.figure(figsize=(13, 10))
plt.scatter(crt.nodes, crt.value, c='r', alpha=.3)
#
t = crt[crt.locality == 0]
plt.plot(t.nodes, t.value, label='Locality 0')
#
t = crt[crt.locality == 1]
plt.plot(t.nodes, t.value, label='Locality 1')
#
t = crt.groupby('nodes', as_index=False).last()
plt.plot(t.nodes, t.value, label='Locality $n - 1$')
#
plt.grid()

plt.legend(loc='upper center', bbox_to_anchor=(
    0.5, -0.05), fancybox=True, shadow=True, ncol=5)
plt.title('Resolve ID - Time')
plt.xlabel('Number of Nodes')
plt.ylabel('Duration of Calls')

plt.gca().xaxis.set_major_locator(ticker.LogLocator(base=2))
plt.gca().set_xlim(left=0.)
plt.gca().set_ylim(bottom=0.)


# Iterate Types

crt = d[(d.sys == 'agas') & (d.proc == 'iterate_types') & (d.type == 'count')]

plt.figure(figsize=(13, 10))
plt.scatter(crt.nodes, crt.value, c='r', alpha=.3)
#
t = crt[crt.locality == 0]
plt.plot(t.nodes, t.value, label='Locality 0')
#
t = crt[crt.locality == 1]
plt.plot(t.nodes, t.value, label='Locality 1')
#
t = crt.groupby('nodes', as_index=False).last()
plt.plot(t.nodes, t.value, label='Locality $n - 1$')
#
plt.grid()

plt.legend(loc='upper center', bbox_to_anchor=(
    0.5, -0.05), fancybox=True, shadow=True, ncol=5)
plt.title('Iterate Type - Count')
plt.xlabel('Number of Nodes')
plt.ylabel('Number of Calls')

plt.gca().xaxis.set_major_locator(ticker.LogLocator(base=2))
plt.gca().set_xlim(left=0.)
plt.gca().set_ylim(bottom=0.)


crt = d[(d.sys == 'agas') & (d.proc == 'iterate_types') & (d.type == 'time')]

plt.figure(figsize=(13, 10))
plt.scatter(crt.nodes, crt.value, c='r', alpha=.3)
#
t = crt[crt.locality == 0]
plt.plot(t.nodes, t.value, label='Locality 0')
#
t = crt[crt.locality == 1]
plt.plot(t.nodes, t.value, label='Locality 1')
#
t = crt.groupby('nodes', as_index=False).last()
plt.plot(t.nodes, t.value, label='Locality $n - 1$')
#
plt.grid()

plt.legend(loc='upper center', bbox_to_anchor=(
    0.5, -0.05), fancybox=True, shadow=True, ncol=5)
plt.title('Iterate Types - Time')
plt.xlabel('Number of Nodes')
plt.ylabel('Duration of Calls')

plt.gca().xaxis.set_major_locator(ticker.LogLocator(base=2))
plt.gca().set_xlim(left=0.)
plt.gca().set_ylim(bottom=0.)


# Get Component Type Name

crt = d[(d.sys == 'agas') & (
    d.proc == 'get_component_typename') & (d.type == 'count')]

plt.figure(figsize=(13, 10))
plt.scatter(crt.nodes, crt.value, c='r', alpha=.3)
#
t = crt[crt.locality == 0]
plt.plot(t.nodes, t.value, label='Locality 0')
#
t = crt[crt.locality == 1]
plt.plot(t.nodes, t.value, label='Locality 1')
#
t = crt.groupby('nodes', as_index=False).last()
plt.plot(t.nodes, t.value, label='Locality $n - 1$')
#
plt.grid()

plt.legend(loc='upper center', bbox_to_anchor=(
    0.5, -0.05), fancybox=True, shadow=True, ncol=5)
plt.title('Get Component Type Name - Count')
plt.xlabel('Number of Nodes')
plt.ylabel('Number of Calls')

plt.gca().xaxis.set_major_locator(ticker.LogLocator(base=2))
plt.gca().set_xlim(left=0.)
plt.gca().set_ylim(bottom=0.)


crt = d[(d.sys == 'agas') & (
    d.proc == 'get_component_typename') & (d.type == 'time')]

plt.figure(figsize=(13, 10))
plt.scatter(crt.nodes, crt.value, c='r', alpha=.3)
#
t = crt[crt.locality == 0]
plt.plot(t.nodes, t.value, label='Locality 0')
#
t = crt[crt.locality == 1]
plt.plot(t.nodes, t.value, label='Locality 1')
#
t = crt.groupby('nodes', as_index=False).last()
plt.plot(t.nodes, t.value, label='Locality $n - 1$')
#
plt.grid()

plt.legend(loc='upper center', bbox_to_anchor=(
    0.5, -0.05), fancybox=True, shadow=True, ncol=5)
plt.title('Get Component Type Name - Time')
plt.xlabel('Number of Nodes')
plt.ylabel('Duration of Calls')

plt.gca().xaxis.set_major_locator(ticker.LogLocator(base=2))
plt.gca().set_xlim(left=0.)
plt.gca().set_ylim(bottom=0.)


# Number of Locality Type

crt = d[(d.sys == 'agas') & (
    d.proc == 'num_localities_type') & (d.type == 'count')]

plt.figure(figsize=(13, 10))
plt.scatter(crt.nodes, crt.value, c='r', alpha=.3)
#
t = crt[crt.locality == 0]
plt.plot(t.nodes, t.value, label='Locality 0')
#
t = crt[crt.locality == 1]
plt.plot(t.nodes, t.value, label='Locality 1')
#
t = crt.groupby('nodes', as_index=False).last()
plt.plot(t.nodes, t.value, label='Locality $n - 1$')
#
plt.grid()

plt.legend(loc='upper center', bbox_to_anchor=(
    0.5, -0.05), fancybox=True, shadow=True, ncol=5)
plt.title('Number of Locality Type - Count')
plt.xlabel('Number of Nodes')
plt.ylabel('Number of Calls')

plt.gca().xaxis.set_major_locator(ticker.LogLocator(base=2))
plt.gca().set_xlim(left=0.)
plt.gca().set_ylim(bottom=0.)


crt = d[(d.sys == 'agas') & (
    d.proc == 'num_localities_type') & (d.type == 'time')]

plt.figure(figsize=(13, 10))
plt.scatter(crt.nodes, crt.value, c='r', alpha=.3)
#
t = crt[crt.locality == 0]
plt.plot(t.nodes, t.value, label='Locality 0')
#
t = crt[crt.locality == 1]
plt.plot(t.nodes, t.value, label='Locality 1')
#
t = crt.groupby('nodes', as_index=False).last()
plt.plot(t.nodes, t.value, label='Locality $n - 1$')
#
plt.grid()

plt.legend(loc='upper center', bbox_to_anchor=(
    0.5, -0.05), fancybox=True, shadow=True, ncol=5)
plt.title('Number of Locality Type - Time')
plt.xlabel('Number of Nodes')
plt.ylabel('Duration of Calls')

plt.gca().xaxis.set_major_locator(ticker.LogLocator(base=2))
plt.gca().set_xlim(left=0.)
plt.gca().set_ylim(bottom=0.)


# Locality Namespace

# Free

crt = d[(d.sys == 'agas') & (d.proc == 'free') & (d.type == 'count')]

plt.figure(figsize=(13, 10))
plt.scatter(crt.nodes, crt.value, c='r', alpha=.3)
#
t = crt[crt.locality == 0]
plt.plot(t.nodes, t.value, label='Locality 0')
#
t = crt[crt.locality == 1]
plt.plot(t.nodes, t.value, label='Locality 1')
#
t = crt.groupby('nodes', as_index=False).last()
plt.plot(t.nodes, t.value, label='Locality $n - 1$')
#
plt.grid()

plt.legend(loc='upper center', bbox_to_anchor=(
    0.5, -0.05), fancybox=True, shadow=True, ncol=5)
plt.title('Free - Count')
plt.xlabel('Number of Nodes')
plt.ylabel('Number of Calls')

plt.gca().xaxis.set_major_locator(ticker.LogLocator(base=2))
plt.gca().set_xlim(left=0.)
plt.gca().set_ylim(bottom=0.)


crt = d[(d.sys == 'agas') & (d.proc == 'free') & (d.type == 'time')]

plt.figure(figsize=(13, 10))
plt.scatter(crt.nodes, crt.value, c='r', alpha=.3)
#
t = crt[crt.locality == 0]
plt.plot(t.nodes, t.value, label='Locality 0')
#
t = crt[crt.locality == 1]
plt.plot(t.nodes, t.value, label='Locality 1')
#
t = crt.groupby('nodes', as_index=False).last()
plt.plot(t.nodes, t.value, label='Locality $n - 1$')
#
plt.grid()

plt.legend(loc='upper center', bbox_to_anchor=(
    0.5, -0.05), fancybox=True, shadow=True, ncol=5)
plt.title('Free - Time')
plt.xlabel('Number of Nodes')
plt.ylabel('Duration of Calls')

plt.gca().xaxis.set_major_locator(ticker.LogLocator(base=2))
plt.gca().set_xlim(left=0.)
plt.gca().set_ylim(bottom=0.)


# Localities

crt = d[(d.sys == 'agas') & (d.proc == 'localities') & (d.type == 'count')]

plt.figure(figsize=(13, 10))
plt.scatter(crt.nodes, crt.value, c='r', alpha=.3)
#
t = crt[crt.locality == 0]
plt.plot(t.nodes, t.value, label='Locality 0')
#
t = crt[crt.locality == 1]
plt.plot(t.nodes, t.value, label='Locality 1')
#
t = crt.groupby('nodes', as_index=False).last()
plt.plot(t.nodes, t.value, label='Locality $n - 1$')
#
plt.grid()

plt.legend(loc='upper center', bbox_to_anchor=(
    0.5, -0.05), fancybox=True, shadow=True, ncol=5)
plt.title('Localities - Count')
plt.xlabel('Number of Nodes')
plt.ylabel('Number of Calls')

plt.gca().xaxis.set_major_locator(ticker.LogLocator(base=2))
plt.gca().set_xlim(left=0.)
plt.gca().set_ylim(bottom=0.)


crt = d[(d.sys == 'agas') & (d.proc == 'localities') & (d.type == 'time')]

plt.figure(figsize=(13, 10))
plt.scatter(crt.nodes, crt.value, c='r', alpha=.3)
#
t = crt[crt.locality == 0]
plt.plot(t.nodes, t.value, label='Locality 0')
#
t = crt[crt.locality == 1]
plt.plot(t.nodes, t.value, label='Locality 1')
#
t = crt.groupby('nodes', as_index=False).last()
plt.plot(t.nodes, t.value, label='Locality $n - 1$')
#
plt.grid()

plt.legend(loc='upper center', bbox_to_anchor=(
    0.5, -0.05), fancybox=True, shadow=True, ncol=5)
plt.title('Localities - Time')
plt.xlabel('Number of Nodes')
plt.ylabel('Duration of Calls')

plt.gca().xaxis.set_major_locator(ticker.LogLocator(base=2))
plt.gca().set_xlim(left=0.)
plt.gca().set_ylim(bottom=0.)


# Number of Localities

crt = d[(d.sys == 'agas') & (d.proc == 'num_localities') & (d.type == 'count')]

plt.figure(figsize=(13, 10))
plt.scatter(crt.nodes, crt.value, c='r', alpha=.3)
#
t = crt[crt.locality == 0]
plt.plot(t.nodes, t.value, label='Locality 0')
#
t = crt[crt.locality == 1]
plt.plot(t.nodes, t.value, label='Locality 1')
#
t = crt.groupby('nodes', as_index=False).last()
plt.plot(t.nodes, t.value, label='Locality $n - 1$')
#
plt.grid()

plt.legend(loc='upper center', bbox_to_anchor=(
    0.5, -0.05), fancybox=True, shadow=True, ncol=5)
plt.title('Number of Localities - Count')
plt.xlabel('Number of Nodes')
plt.ylabel('Number of Calls')

plt.gca().xaxis.set_major_locator(ticker.LogLocator(base=2))
plt.gca().set_xlim(left=0.)
plt.gca().set_ylim(bottom=0.)


crt = d[(d.sys == 'agas') & (d.proc == 'num_localities') & (d.type == 'time')]

plt.figure(figsize=(13, 10))
plt.scatter(crt.nodes, crt.value, c='r', alpha=.3)
#
t = crt[crt.locality == 0]
plt.plot(t.nodes, t.value, label='Locality 0')
#
t = crt[crt.locality == 1]
plt.plot(t.nodes, t.value, label='Locality 1')
#
t = crt.groupby('nodes', as_index=False).last()
plt.plot(t.nodes, t.value, label='Locality $n - 1$')
#
plt.grid()

plt.legend(loc='upper center', bbox_to_anchor=(
    0.5, -0.05), fancybox=True, shadow=True, ncol=5)
plt.title('Number of Localities - Time')
plt.xlabel('Number of Nodes')
plt.ylabel('Duration of Calls')

plt.gca().xaxis.set_major_locator(ticker.LogLocator(base=2))
plt.gca().set_xlim(left=0.)
plt.gca().set_ylim(bottom=0.)


# Resolve Locality

crt = d[(d.sys == 'agas') & (d.proc == 'resolve_locality') & (d.type == 'count')]

plt.figure(figsize=(13, 10))
plt.scatter(crt.nodes, crt.value, c='r', alpha=.3)
#
t = crt[crt.locality == 0]
plt.plot(t.nodes, t.value, label='Locality 0')
#
t = crt[crt.locality == 1]
plt.plot(t.nodes, t.value, label='Locality 1')
#
t = crt.groupby('nodes', as_index=False).last()
plt.plot(t.nodes, t.value, label='Locality $n - 1$')
#
plt.grid()

plt.legend(loc='upper center', bbox_to_anchor=(
    0.5, -0.05), fancybox=True, shadow=True, ncol=5)
plt.title('Resolve Locality - Count')
plt.xlabel('Number of Nodes')
plt.ylabel('Number of Calls')

plt.gca().xaxis.set_major_locator(ticker.LogLocator(base=2))
plt.gca().set_xlim(left=0.)
plt.gca().set_ylim(bottom=0.)


crt = d[(d.sys == 'agas') & (d.proc == 'resolve_locality') & (d.type == 'time')]

plt.figure(figsize=(13, 10))
plt.scatter(crt.nodes, crt.value, c='r', alpha=.3)
#
t = crt[crt.locality == 0]
plt.plot(t.nodes, t.value, label='Locality 0')
#
t = crt[crt.locality == 1]
plt.plot(t.nodes, t.value, label='Locality 1')
#
t = crt.groupby('nodes', as_index=False).last()
plt.plot(t.nodes, t.value, label='Locality $n - 1$')
#
plt.grid()

plt.legend(loc='upper center', bbox_to_anchor=(
    0.5, -0.05), fancybox=True, shadow=True, ncol=5)
plt.title('Resolve Locality - Time')
plt.xlabel('Number of Nodes')
plt.ylabel('Duration of Calls')

plt.gca().xaxis.set_major_locator(ticker.LogLocator(base=2))
plt.gca().set_xlim(left=0.)
plt.gca().set_ylim(bottom=0.)


# Number of Threads

crt = d[(d.sys == 'agas') & (d.proc == 'num_threads') & (d.type == 'count')]

plt.figure(figsize=(13, 10))
plt.scatter(crt.nodes, crt.value, c='r', alpha=.3)
#
t = crt[crt.locality == 0]
plt.plot(t.nodes, t.value, label='Locality 0')
#
t = crt[crt.locality == 1]
plt.plot(t.nodes, t.value, label='Locality 1')
#
t = crt.groupby('nodes', as_index=False).last()
plt.plot(t.nodes, t.value, label='Locality $n - 1$')
#
plt.grid()

plt.legend(loc='upper center', bbox_to_anchor=(
    0.5, -0.05), fancybox=True, shadow=True, ncol=5)
plt.title('Number of Threads - Count')
plt.xlabel('Number of Nodes')
plt.ylabel('Number of Calls')

plt.gca().xaxis.set_major_locator(ticker.LogLocator(base=2))
plt.gca().set_xlim(left=0.)
plt.gca().set_ylim(bottom=0.)


crt = d[(d.sys == 'agas') & (d.proc == 'num_threads') & (d.type == 'time')]

plt.figure(figsize=(13, 10))
plt.scatter(crt.nodes, crt.value, c='r', alpha=.3)
#
t = crt[crt.locality == 0]
plt.plot(t.nodes, t.value, label='Locality 0')
#
t = crt[crt.locality == 1]
plt.plot(t.nodes, t.value, label='Locality 1')
#
t = crt.groupby('nodes', as_index=False).last()
plt.plot(t.nodes, t.value, label='Locality $n - 1$')
#
plt.grid()

plt.legend(loc='upper center', bbox_to_anchor=(
    0.5, -0.05), fancybox=True, shadow=True, ncol=5)
plt.title('Number of Threads - Time')
plt.xlabel('Number of Nodes')
plt.ylabel('Duration of Calls')

plt.gca().xaxis.set_major_locator(ticker.LogLocator(base=2))
plt.gca().set_xlim(left=0.)
plt.gca().set_ylim(bottom=0.)


# Symbol Namespace

# Bind

crt = d[(d.sys == 'agas') & (d.proc == 'bind') & (d.type == 'count')]

plt.figure(figsize=(13, 10))
plt.scatter(crt.nodes, crt.value, c='r', alpha=.3)
#
t = crt[crt.locality == 0]
plt.plot(t.nodes, t.value, label='Locality 0')
#
t = crt[crt.locality == 1]
plt.plot(t.nodes, t.value, label='Locality 1')
#
t = crt.groupby('nodes', as_index=False).last()
plt.plot(t.nodes, t.value, label='Locality $n - 1$')
#
plt.grid()

plt.legend(loc='upper center', bbox_to_anchor=(
    0.5, -0.05), fancybox=True, shadow=True, ncol=5)
plt.title('Bind - Count')
plt.xlabel('Number of Nodes')
plt.ylabel('Number of Calls')

plt.gca().xaxis.set_major_locator(ticker.LogLocator(base=2))
plt.gca().set_xlim(left=0.)
plt.gca().set_ylim(bottom=0.)


crt = d[(d.sys == 'agas') & (d.proc == 'bind') & (d.type == 'time')]

plt.figure(figsize=(13, 10))
plt.scatter(crt.nodes, crt.value, c='r', alpha=.3)
#
t = crt[crt.locality == 0]
plt.plot(t.nodes, t.value, label='Locality 0')
#
t = crt[crt.locality == 1]
plt.plot(t.nodes, t.value, label='Locality 1')
#
t = crt.groupby('nodes', as_index=False).last()
plt.plot(t.nodes, t.value, label='Locality $n - 1$')
#
plt.grid()

plt.legend(loc='upper center', bbox_to_anchor=(
    0.5, -0.05), fancybox=True, shadow=True, ncol=5)
plt.title('Bind - Time')
plt.xlabel('Number of Nodes')
plt.ylabel('Duration of Calls')

plt.gca().xaxis.set_major_locator(ticker.LogLocator(base=2))
plt.gca().set_xlim(left=0.)
plt.gca().set_ylim(bottom=0.)


# Unbind

crt = d[(d.sys == 'agas') & (d.proc == 'unbind') & (d.type == 'count')]

plt.figure(figsize=(13, 10))
plt.scatter(crt.nodes, crt.value, c='r', alpha=.3)
#
t = crt[crt.locality == 0]
plt.plot(t.nodes, t.value, label='Locality 0')
#
t = crt[crt.locality == 1]
plt.plot(t.nodes, t.value, label='Locality 1')
#
t = crt.groupby('nodes', as_index=False).last()
plt.plot(t.nodes, t.value, label='Locality $n - 1$')
#
plt.grid()

plt.legend(loc='upper center', bbox_to_anchor=(
    0.5, -0.05), fancybox=True, shadow=True, ncol=5)
plt.title('Unbind - Count')
plt.xlabel('Number of Nodes')
plt.ylabel('Number of Calls')

plt.gca().xaxis.set_major_locator(ticker.LogLocator(base=2))
plt.gca().set_xlim(left=0.)
plt.gca().set_ylim(bottom=0.)


crt = d[(d.sys == 'agas') & (d.proc == 'unbind') & (d.type == 'time')]

plt.figure(figsize=(13, 10))
plt.scatter(crt.nodes, crt.value, c='r', alpha=.3)
#
t = crt[crt.locality == 0]
plt.plot(t.nodes, t.value, label='Locality 0')
#
t = crt[crt.locality == 1]
plt.plot(t.nodes, t.value, label='Locality 1')
#
t = crt.groupby('nodes', as_index=False).last()
plt.plot(t.nodes, t.value, label='Locality $n - 1$')
#
plt.grid()

plt.legend(loc='upper center', bbox_to_anchor=(
    0.5, -0.05), fancybox=True, shadow=True, ncol=5)
plt.title('Unbind - Time')
plt.xlabel('Number of Nodes')
plt.ylabel('Duration of Calls')

plt.gca().xaxis.set_major_locator(ticker.LogLocator(base=2))
plt.gca().set_xlim(left=0.)
plt.gca().set_ylim(bottom=0.)


# Resolve

crt = d[(d.sys == 'agas') & (d.proc == 'resolve') & (d.type == 'count')]

plt.figure(figsize=(13, 10))
plt.scatter(crt.nodes, crt.value, c='r', alpha=.3)
#
t = crt[crt.locality == 0]
plt.plot(t.nodes, t.value, label='Locality 0')
#
t = crt[crt.locality == 1]
plt.plot(t.nodes, t.value, label='Locality 1')
#
t = crt.groupby('nodes', as_index=False).last()
plt.plot(t.nodes, t.value, label='Locality $n - 1$')
#
plt.grid()

plt.legend(loc='upper center', bbox_to_anchor=(
    0.5, -0.05), fancybox=True, shadow=True, ncol=5)
plt.title('Resolve - Count')
plt.xlabel('Number of Nodes')
plt.ylabel('Number of Calls')

plt.gca().xaxis.set_major_locator(ticker.LogLocator(base=2))
plt.gca().set_xlim(left=0.)
plt.gca().set_ylim(bottom=0.)


crt = d[(d.sys == 'agas') & (d.proc == 'resolve') & (d.type == 'time')]

plt.figure(figsize=(13, 10))
plt.scatter(crt.nodes, crt.value, c='r', alpha=.3)
#
t = crt[crt.locality == 0]
plt.plot(t.nodes, t.value, label='Locality 0')
#
t = crt[crt.locality == 1]
plt.plot(t.nodes, t.value, label='Locality 1')
#
t = crt.groupby('nodes', as_index=False).last()
plt.plot(t.nodes, t.value, label='Locality $n - 1$')
#
plt.grid()

plt.legend(loc='upper center', bbox_to_anchor=(
    0.5, -0.05), fancybox=True, shadow=True, ncol=5)
plt.title('Resolve - Time')
plt.xlabel('Number of Nodes')
plt.ylabel('Duration of Calls')

plt.gca().xaxis.set_major_locator(ticker.LogLocator(base=2))
plt.gca().set_xlim(left=0.)
plt.gca().set_ylim(bottom=0.)


# Iterate Names

crt = d[(d.sys == 'agas') & (d.proc == 'iterate_names') & (d.type == 'count')]

plt.figure(figsize=(13, 10))
plt.scatter(crt.nodes, crt.value, c='r', alpha=.3)
#
t = crt[crt.locality == 0]
plt.plot(t.nodes, t.value, label='Locality 0')
#
t = crt[crt.locality == 1]
plt.plot(t.nodes, t.value, label='Locality 1')
#
t = crt.groupby('nodes', as_index=False).last()
plt.plot(t.nodes, t.value, label='Locality $n - 1$')
#
plt.grid()

plt.legend(loc='upper center', bbox_to_anchor=(
    0.5, -0.05), fancybox=True, shadow=True, ncol=5)
plt.title('Iterate Names - Count')
plt.xlabel('Number of Nodes')
plt.ylabel('Number of Calls')

plt.gca().xaxis.set_major_locator(ticker.LogLocator(base=2))
plt.gca().set_xlim(left=0.)
plt.gca().set_ylim(bottom=0.)


crt = d[(d.sys == 'agas') & (d.proc == 'iterate_names') & (d.type == 'time')]

plt.figure(figsize=(13, 10))
plt.scatter(crt.nodes, crt.value, c='r', alpha=.3)
#
t = crt[crt.locality == 0]
plt.plot(t.nodes, t.value, label='Locality 0')
#
t = crt[crt.locality == 1]
plt.plot(t.nodes, t.value, label='Locality 1')
#
t = crt.groupby('nodes', as_index=False).last()
plt.plot(t.nodes, t.value, label='Locality $n - 1$')
#
plt.grid()

plt.legend(loc='upper center', bbox_to_anchor=(
    0.5, -0.05), fancybox=True, shadow=True, ncol=5)
plt.title('Iterate Names - Time')
plt.xlabel('Number of Nodes')
plt.ylabel('Duration of Calls')

plt.gca().xaxis.set_major_locator(ticker.LogLocator(base=2))
plt.gca().set_xlim(left=0.)
plt.gca().set_ylim(bottom=0.)


# On Symbol Namespace Event

crt = d[(d.sys == 'agas') & (
    d.proc == 'on_symbol_namespace_event') & (d.type == 'count')]

plt.figure(figsize=(13, 10))
plt.scatter(crt.nodes, crt.value, c='r', alpha=.3)
#
t = crt[crt.locality == 0]
plt.plot(t.nodes, t.value, label='Locality 0')
#
t = crt[crt.locality == 1]
plt.plot(t.nodes, t.value, label='Locality 1')
#
t = crt.groupby('nodes', as_index=False).last()
plt.plot(t.nodes, t.value, label='Locality $n - 1$')
#
plt.grid()

plt.legend(loc='upper center', bbox_to_anchor=(
    0.5, -0.05), fancybox=True, shadow=True, ncol=5)
plt.title('On Symbol Namespace Event - Count')
plt.xlabel('Number of Nodes')
plt.ylabel('Number of Calls')

plt.gca().xaxis.set_major_locator(ticker.LogLocator(base=2))
plt.gca().set_xlim(left=0.)
plt.gca().set_ylim(bottom=0.)


crt = d[(d.sys == 'agas') & (
    d.proc == 'on_symbol_namespace_event') & (d.type == 'time')]

plt.figure(figsize=(13, 10))
plt.scatter(crt.nodes, crt.value, c='r', alpha=.3)
#
t = crt[crt.locality == 0]
plt.plot(t.nodes, t.value, label='Locality 0')
#
t = crt[crt.locality == 1]
plt.plot(t.nodes, t.value, label='Locality 1')
#
t = crt.groupby('nodes', as_index=False).last()
plt.plot(t.nodes, t.value, label='Locality $n - 1$')
#
plt.grid()

plt.legend(loc='upper center', bbox_to_anchor=(
    0.5, -0.05), fancybox=True, shadow=True, ncol=5)
plt.title('On Symbol Namespace Event - Time')
plt.xlabel('Number of Nodes')
plt.ylabel('Duration of Calls')

plt.gca().xaxis.set_major_locator(ticker.LogLocator(base=2))
plt.gca().set_xlim(left=0.)
plt.gca().set_ylim(bottom=0.)


# ---

# AGAS Cache

# Number of Cache Entries

crt = d[(d.sys == 'agas') & (d.proc == 'cache.entries') & (d.type == 'count')]

plt.figure(figsize=(13, 10))
plt.scatter(crt.nodes, crt.value, c='r', alpha=.3)
#
t = crt[crt.locality == 0]
plt.plot(t.nodes, t.value, label='Locality 0')
#
t = crt[crt.locality == 1]
plt.plot(t.nodes, t.value, label='Locality 1')
#
t = crt.groupby('nodes', as_index=False).last()
plt.plot(t.nodes, t.value, label='Locality $n - 1$')
#
plt.grid()

plt.legend(loc='upper center', bbox_to_anchor=(
    0.5, -0.05), fancybox=True, shadow=True, ncol=5)
plt.title('AGAS Cache Entries - Count')
plt.xlabel('Number of Nodes')
plt.ylabel('Number of AGAS Cache Entries')

plt.gca().xaxis.set_major_locator(ticker.LogLocator(base=2))
plt.gca().set_xlim(left=0.)
plt.gca().set_ylim(bottom=0.)


# AGAS Cache Insertions

crt = d[(d.sys == 'agas') & (d.proc == 'cache.insertions') & (d.type == 'count')]

plt.figure(figsize=(13, 10))
plt.scatter(crt.nodes, crt.value, c='r', alpha=.3)
#
t = crt[crt.locality == 0]
plt.plot(t.nodes, t.value, label='Locality 0')
#
t = crt[crt.locality == 1]
plt.plot(t.nodes, t.value, label='Locality 1')
#
t = crt.groupby('nodes', as_index=False).last()
plt.plot(t.nodes, t.value, label='Locality $n - 1$')
#
plt.grid()

plt.legend(loc='upper center', bbox_to_anchor=(
    0.5, -0.05), fancybox=True, shadow=True, ncol=5)
plt.title('AGAS Cache Insertions - Count')
plt.xlabel('Number of Nodes')
plt.ylabel('Number of AGAS Cache Insertions')

plt.gca().xaxis.set_major_locator(ticker.LogLocator(base=2))
plt.gca().set_xlim(left=0.)
plt.gca().set_ylim(bottom=0.)


# AGAS Cache Evictions

crt = d[(d.sys == 'agas') & (d.proc == 'cache.evictions') & (d.type == 'count')]

plt.figure(figsize=(13, 10))
plt.scatter(crt.nodes, crt.value, c='r', alpha=.3)
#
t = crt[crt.locality == 0]
plt.plot(t.nodes, t.value, label='Locality 0')
#
t = crt[crt.locality == 1]
plt.plot(t.nodes, t.value, label='Locality 1')
#
t = crt.groupby('nodes', as_index=False).last()
plt.plot(t.nodes, t.value, label='Locality $n - 1$')
#
plt.grid()

plt.legend(loc='upper center', bbox_to_anchor=(
    0.5, -0.05), fancybox=True, shadow=True, ncol=5)
plt.title('AGAS Cache Evictions - Count')
plt.xlabel('Number of Nodes')
plt.ylabel('Number of AGAS Cache Evictions')

plt.gca().xaxis.set_major_locator(ticker.LogLocator(base=2))
plt.gca().set_xlim(left=0.)
plt.gca().set_ylim(bottom=0.)


# AGAS Cache Hit Rate
#
# * $\textit{hits}$: `/agas{locality#*/total}/count/cache/hits`
# * $\textit{misses}$: `/agas{locality#*/total}/count/cache/misses`
#
# $$
# \textit{miss rate} = \frac{\textit{misses}}{\textit{misses} + \textit{hits}}
# $$

crt_h = d[(d.sys == 'agas') & (d.proc == 'cache.hits') & (d.type == 'count')]
crt_m = d[(d.sys == 'agas') & (d.proc == 'cache.misses') & (d.type == 'count')]

crt_m = crt_m.set_index(crt_h.index)

crt = crt_h[['nodes', 'value', 'locality']]
# crt.is_copy = False # Disable the warning
crt['rate'] = crt_h.value / (crt_h.value + crt_m.value)

plt.figure(figsize=(13, 10))
plt.scatter(crt.nodes, crt.rate, c='r', alpha=.3)

t = crt[crt.locality == 0]
plt.plot(t.nodes, t.rate, label='Locality 0')

t = crt[crt.locality == 1]
plt.plot(t.nodes, t.rate, label='Locality 1')

t = crt.groupby('nodes', as_index=False).last()
plt.plot(t.nodes, t.rate, label='Locality $n - 1$')

plt.grid()

plt.legend(loc='upper center', bbox_to_anchor=(
    0.5, -0.05), fancybox=True, shadow=True, ncol=5)
plt.title('AGAS Cache Hit Rate')
plt.xlabel('Number of Nodes')
plt.ylabel('Rate')

plt.gca().xaxis.set_major_locator(ticker.LogLocator(base=2))
plt.gca().set_xlim(left=0.)
plt.gca().yaxis.set_major_formatter(PercentFormatter)
plt.gca().set_ylim(bottom=0.)


# Get Entry

crt = d[(d.sys == 'agas') & (d.proc == 'cache.get_entry') & (d.type == 'time')]

plt.figure(figsize=(13, 10))
plt.scatter(crt.nodes, crt.value, c='r', alpha=.3)

t = crt[crt.locality == 0]
plt.plot(t.nodes, t.value, label='Locality 0')

t = crt[crt.locality == 1]
plt.plot(t.nodes, t.value, label='Locality 1')
#
t = crt.groupby('nodes', as_index=False).last()
plt.plot(t.nodes, t.value, label='Locality $n - 1$')
#
plt.grid()

plt.legend(loc='upper center', bbox_to_anchor=(
    0.5, -0.05), fancybox=True, shadow=True, ncol=5)
plt.title('AGAS Cache Get Entry Duration')
plt.xlabel('Number of Nodes')
plt.ylabel('Duration')

plt.gca().xaxis.set_major_locator(ticker.LogLocator(base=2))
plt.gca().set_xlim(left=0.)
plt.gca().set_ylim(bottom=0.)


# Insert Entry

crt = d[(d.sys == 'agas') & (d.proc == 'cache.insert_entry') & (d.type == 'time')]

plt.figure(figsize=(13, 10))
plt.scatter(crt.nodes, crt.value, c='r', alpha=.3)

t = crt[crt.locality == 0]
plt.plot(t.nodes, t.value, label='Locality 0')

t = crt[crt.locality == 1]
plt.plot(t.nodes, t.value, label='Locality 1')
#
t = crt.groupby('nodes', as_index=False).last()
plt.plot(t.nodes, t.value, label='Locality $n - 1$')
#
plt.grid()

plt.legend(loc='upper center', bbox_to_anchor=(
    0.5, -0.05), fancybox=True, shadow=True, ncol=5)
plt.title('AGAS Cache Insert')
plt.xlabel('Number of Nodes')
plt.ylabel('Duration of Insert Call')

plt.gca().xaxis.set_major_locator(ticker.LogLocator(base=2))
plt.gca().set_xlim(left=0.)
plt.gca().set_ylim(bottom=0.)


# Update Entry

crt = d[(d.sys == 'agas') & (
    d.proc == 'cache.update_entry') & (d.type == 'count')]

plt.figure(figsize=(13, 10))
plt.scatter(crt.nodes, crt.value, c='r', alpha=.3)

t = crt[crt.locality == 0]
plt.plot(t.nodes, t.value, label='Locality 0')

t = crt[crt.locality == 1]
plt.plot(t.nodes, t.value, label='Locality 1')
#
t = crt.groupby('nodes', as_index=False).last()
plt.plot(t.nodes, t.value, label='Locality $n - 1$')
#
plt.grid()

plt.legend(loc='upper center', bbox_to_anchor=(
    0.5, -0.05), fancybox=True, shadow=True, ncol=5)
plt.title('AGAS Cache Update Calls')
plt.xlabel('Number of Nodes')
plt.ylabel('Number of Updates')

plt.gca().xaxis.set_major_locator(ticker.LogLocator(base=2))
plt.gca().set_xlim(left=0.)
plt.gca().set_ylim(bottom=0.)


crt = d[(d.sys == 'agas') & (d.proc == 'cache.update_entry') & (d.type == 'time')]

if crt.size > 0:
    plt.figure(figsize=(13, 10))
    plt.scatter(crt.nodes, crt.value, c='r', alpha=.3)

    t = crt[crt.locality == 0]
    plt.plot(t.nodes, t.value, label='Locality 0')

    t = crt[crt.locality == 1]
    plt.plot(t.nodes, t.value, label='Locality 1')
    #
    t = crt.groupby('nodes', as_index=False).last()
    plt.plot(t.nodes, t.value, label='Locality $n - 1$')
    #
    plt.grid()

    plt.legend(loc='upper center', bbox_to_anchor=(
        0.5, -0.05), fancybox=True, shadow=True, ncol=5)
    plt.title('AGAS Cache Update Call Duration')
    plt.xlabel('Number of Nodes')
    plt.ylabel('Duration of Updates')

    plt.gca().xaxis.set_major_locator(ticker.LogLocator(base=2))
    plt.gca().set_xlim(left=0.)
    plt.gca().set_ylim(bottom=0.)


# Erase Entry

crt = d[(d.sys == 'agas') & (d.proc == 'cache.erase_entry') & (d.type == 'time')]

plt.figure(figsize=(13, 10))
plt.scatter(crt.nodes, crt.value, c='r', alpha=.3)

t = crt[crt.locality == 0]
plt.plot(t.nodes, t.value, label='Locality 0')

t = crt[crt.locality == 1]
plt.plot(t.nodes, t.value, label='Locality 1')
#
t = crt.groupby('nodes', as_index=False).last()
plt.plot(t.nodes, t.value, label='Locality $n - 1$')
#
plt.grid()

plt.legend(loc='upper center', bbox_to_anchor=(
    0.5, -0.05), fancybox=True, shadow=True, ncol=5)
plt.title('AGAS Cache Erase')
plt.xlabel('Number of Nodes')
plt.ylabel('Duration of Erase Calls')

plt.gca().xaxis.set_major_locator(ticker.LogLocator(base=2))
plt.gca().set_xlim(left=0.)
plt.gca().set_ylim(bottom=0.)


# ***

# Overview

# Primary Namespace

crt = d[(d.sys == 'agas') & (d.proc == 'primary') & (d.type == 'count')]

plt.figure(figsize=(13, 10))
plt.scatter(crt.nodes, crt.value, c='r', alpha=.3)

t = crt[crt.locality == 0]
plt.plot(t.nodes, t.value, label='Locality 0')

t = crt[crt.locality == 1]
plt.plot(t.nodes, t.value, label='Locality 1')
#
t = crt.groupby('nodes', as_index=False).last()
plt.plot(t.nodes, t.value, label='Locality $n - 1$')
#
plt.grid()

plt.legend(loc='upper center', bbox_to_anchor=(
    0.5, -0.05), fancybox=True, shadow=True, ncol=5)
plt.title('AGAS Primary Namespace Events')
plt.xlabel('Number of Nodes')
plt.ylabel('Number of Events')

plt.gca().xaxis.set_major_locator(ticker.LogLocator(base=2))
plt.gca().set_xlim(left=0.)
plt.gca().set_ylim(bottom=0.)


crt = d[(d.sys == 'agas') & (d.proc == 'primary') & (d.type == 'time')]

if crt.size > 0:
    plt.figure(figsize=(13, 10))
    plt.scatter(crt.nodes, crt.value, c='r', alpha=.3)

    t = crt[crt.locality == 0]
    plt.plot(t.nodes, t.value, label='Locality 0')

    t = crt[crt.locality == 1]
    plt.plot(t.nodes, t.value, label='Locality 1')
    #
    t = crt.groupby('nodes', as_index=False).last()
    plt.plot(t.nodes, t.value, label='Locality $n - 1$')
    #
    plt.grid()

    plt.legend(loc='upper center', bbox_to_anchor=(
        0.5, -0.05), fancybox=True, shadow=True, ncol=5)
    plt.title('AGAS Primary Namespace Events')
    plt.xlabel('Number of Nodes')
    plt.ylabel('Duration of Events')

    plt.gca().xaxis.set_major_locator(ticker.LogLocator(base=2))
    plt.gca().set_xlim(left=0.)
    plt.gca().set_ylim(bottom=0.)


# Component Namespace

crt = d[(d.sys == 'agas') & (d.proc == 'component') & (d.type == 'count')]

plt.figure(figsize=(13, 10))
plt.scatter(crt.nodes, crt.value, c='r', alpha=.3)

t = crt[crt.locality == 0]
plt.plot(t.nodes, t.value, label='Locality 0')

t = crt[crt.locality == 1]
plt.plot(t.nodes, t.value, label='Locality 1')
#
t = crt.groupby('nodes', as_index=False).last()
plt.plot(t.nodes, t.value, label='Locality $n - 1$')
#
plt.grid()

plt.legend(loc='upper center', bbox_to_anchor=(
    0.5, -0.05), fancybox=True, shadow=True, ncol=5)
plt.title('AGAS Component Namespace Events')
plt.xlabel('Number of Nodes')
plt.ylabel('Number of Events')

plt.gca().xaxis.set_major_locator(ticker.LogLocator(base=2))
plt.gca().set_xlim(left=0.)
plt.gca().set_ylim(bottom=0.)


crt = d[(d.sys == 'agas') & (d.proc == 'component') & (d.type == 'time')]

if crt.size > 0:
    plt.figure(figsize=(13, 10))
    plt.scatter(crt.nodes, crt.value, c='r', alpha=.3)

    t = crt[crt.locality == 0]
    plt.plot(t.nodes, t.value, label='Locality 0')

    t = crt[crt.locality == 1]
    plt.plot(t.nodes, t.value, label='Locality 1')
    #
    t = crt.groupby('nodes', as_index=False).last()
    plt.plot(t.nodes, t.value, label='Locality $n - 1$')
    #
    plt.grid()

    plt.legend(loc='upper center', bbox_to_anchor=(
        0.5, -0.05), fancybox=True, shadow=True, ncol=5)
    plt.title('AGAS Component Namespace Events')
    plt.xlabel('Number of Nodes')
    plt.ylabel('Duration of Events')

    plt.gca().xaxis.set_major_locator(ticker.LogLocator(base=2))
    plt.gca().set_xlim(left=0.)
    plt.gca().set_ylim(bottom=0.)


# Locality Namespace

crt = d[(d.sys == 'agas') & (d.proc == 'locality') & (d.type == 'count')]

plt.figure(figsize=(13, 10))
plt.scatter(crt.nodes, crt.value, c='r', alpha=.3)

t = crt[crt.locality == 0]
plt.plot(t.nodes, t.value, label='Locality 0')

t = crt[crt.locality == 1]
plt.plot(t.nodes, t.value, label='Locality 1')
#
t = crt.groupby('nodes', as_index=False).last()
plt.plot(t.nodes, t.value, label='Locality $n - 1$')
#
plt.grid()

plt.legend(loc='upper center', bbox_to_anchor=(
    0.5, -0.05), fancybox=True, shadow=True, ncol=5)
plt.title('AGAS Locality Namespace Events')
plt.xlabel('Number of Nodes')
plt.ylabel('Number of Events')

plt.gca().xaxis.set_major_locator(ticker.LogLocator(base=2))
plt.gca().set_xlim(left=0.)
plt.gca().set_ylim(bottom=0.)


crt = d[(d.sys == 'agas') & (d.proc == 'locality') & (d.type == 'time')]

if crt.size > 0:
    plt.figure(figsize=(13, 10))
    plt.scatter(crt.nodes, crt.value, c='r', alpha=.3)

    t = crt[crt.locality == 0]
    plt.plot(t.nodes, t.value, label='Locality 0')

    t = crt[crt.locality == 1]
    plt.plot(t.nodes, t.value, label='Locality 1')
    #
    t = crt.groupby('nodes', as_index=False).last()
    plt.plot(t.nodes, t.value, label='Locality $n - 1$')
    #
    plt.grid()

    plt.legend(loc='upper center', bbox_to_anchor=(
        0.5, -0.05), fancybox=True, shadow=True, ncol=5)
    plt.title('AGAS Locality Namespace Events')
    plt.xlabel('Number of Nodes')
    plt.ylabel('Duration of Events')

    plt.gca().xaxis.set_major_locator(ticker.LogLocator(base=2))
    plt.gca().set_xlim(left=0.)
    plt.gca().set_ylim(bottom=0.)


# Symbol Namespace

crt = d[(d.sys == 'agas') & (d.proc == 'symbol') & (d.type == 'count')]

plt.figure(figsize=(13, 10))
plt.scatter(crt.nodes, crt.value, c='r', alpha=.3)

t = crt[crt.locality == 0]
plt.plot(t.nodes, t.value, label='Locality 0')

t = crt[crt.locality == 1]
plt.plot(t.nodes, t.value, label='Locality 1')
#
t = crt.groupby('nodes', as_index=False).last()
plt.plot(t.nodes, t.value, label='Locality $n - 1$')
#
plt.grid()

plt.legend(loc='upper center', bbox_to_anchor=(
    0.5, -0.05), fancybox=True, shadow=True, ncol=5)
plt.title('AGAS Symbol Namespace Events')
plt.xlabel('Number of Nodes')
plt.ylabel('Number of Events')

plt.gca().xaxis.set_major_locator(ticker.LogLocator(base=2))
plt.gca().set_xlim(left=0.)
plt.gca().set_ylim(bottom=0.)


crt = d[(d.sys == 'agas') & (d.proc == 'symbol') & (d.type == 'time')]

if crt.size > 0:
    plt.figure(figsize=(13, 10))
    plt.scatter(crt.nodes, crt.value, c='r', alpha=.3)

    t = crt[crt.locality == 0]
    plt.plot(t.nodes, t.value, label='Locality 0')

    t = crt[crt.locality == 1]
    plt.plot(t.nodes, t.value, label='Locality 1')
    #
    t = crt.groupby('nodes', as_index=False).last()
    plt.plot(t.nodes, t.value, label='Locality $n - 1$')
    #
    plt.grid()

    plt.legend(loc='upper center', bbox_to_anchor=(
        0.5, -0.05), fancybox=True, shadow=True, ncol=5)
    plt.title('AGAS Symbol Namespace Events')
    plt.xlabel('Number of Nodes')
    plt.ylabel('Duration of Events')

    plt.gca().xaxis.set_major_locator(ticker.LogLocator(base=2))
    plt.gca().set_xlim(left=0.)
    plt.gca().set_ylim(bottom=0.)
