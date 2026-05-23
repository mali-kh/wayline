# Data-agent resource overhead — `overhead-stress-k3.csv`

Time window 253s, 441 samples across 9 agents.

| node | CPU mean | CPU peak | RSS mean | RSS peak | bytes in (MB) | bytes out (MB) | PUT count | peak inflight |
|------|---------:|---------:|---------:|---------:|--------------:|---------------:|----------:|--------------:|
| anrg-3 | 10.5 m | 40 m | 161.4 MB | 164 MB | 182.4 | 42.5 | 6 | 0 |
| anrg-9 | 12.4 m | 18 m | 12.3 MB | 13 MB | 0.6 | 0.0 | 15 | 0 |
| anrg-2 | 1.4 m | 2 m | 5.1 MB | 6 MB | 0.0 | 0.0 | 0 | 0 |
| anrg-1 | 12.2 m | 39 m | 164.4 MB | 166 MB | 144.5 | 37.7 | 6 | 3 |
| anrg-5 | 15.0 m | 66 m | 260.4 MB | 270 MB | 493.7 | 73.4 | 6 | 2 |
| anrg-6 | 15.4 m | 39 m | 44.9 MB | 46 MB | 83.2 | 0.2 | 15 | 0 |
| anrg-4 | 14.9 m | 76 m | 191.3 MB | 239 MB | 493.5 | 68.7 | 6 | 3 |
| anrg-7 | 14.9 m | 23 m | 144.8 MB | 145 MB | 8.5 | 0.3 | 12 | 0 |
| anrg-8 | 19.2 m | 96 m | 225.6 MB | 227 MB | 162.8 | 13.9 | 18 | 0 |

Aggregate peak across 9 agents: CPU 399 m (0.40 cores), RSS 1276 MB. Bounded-fanout invariant: max inflight at any agent 3 (config max = 4).
