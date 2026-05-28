# Data-agent resource overhead — `overhead-d120-png.csv`

Time window 171s, 225 samples across 9 agents.

| node | CPU mean | CPU peak | RSS mean | RSS peak | bytes in (MB) | bytes out (MB) | PUT count | peak inflight |
|------|---------:|---------:|---------:|---------:|--------------:|---------------:|----------:|--------------:|
| anrg-3 | 6.3 m | 20 m | 157.2 MB | 159 MB | 115.1 | 68.5 | 2 | 1 |
| anrg-9 | 7.0 m | 11 m | 11.7 MB | 13 MB | 0.2 | 0.0 | 5 | 0 |
| anrg-2 | 1.0 m | 2 m | 4.9 MB | 5 MB | 0.0 | 0.0 | 0 | 0 |
| anrg-1 | 7.9 m | 22 m | 160.2 MB | 165 MB | 96.8 | 61.2 | 2 | 0 |
| anrg-5 | 10.2 m | 22 m | 265.6 MB | 271 MB | 269.5 | 129.4 | 2 | 1 |
| anrg-6 | 6.4 m | 11 m | 42.4 MB | 44 MB | 2.9 | 0.1 | 4 | 0 |
| anrg-4 | 9.0 m | 26 m | 235.9 MB | 243 MB | 257.0 | 115.4 | 2 | 1 |
| anrg-7 | 17.0 m | 86 m | 143.5 MB | 145 MB | 130.7 | 0.0 | 3 | 0 |
| anrg-8 | 26.9 m | 96 m | 220.0 MB | 224 MB | 249.8 | 2.9 | 7 | 0 |

Aggregate peak across 9 agents: CPU 296 m (0.30 cores), RSS 1269 MB. Bounded-fanout invariant: max inflight at any agent 1 (config max = 4).
