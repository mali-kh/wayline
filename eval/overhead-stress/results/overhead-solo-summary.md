# Data-agent resource overhead — `overhead-solo.csv`

Time window 125s, 175 samples across 9 agents.

| node | CPU mean | CPU peak | RSS mean | RSS peak | bytes in (MB) | bytes out (MB) | PUT count | peak inflight |
|------|---------:|---------:|---------:|---------:|--------------:|---------------:|----------:|--------------:|
| anrg-7 | 15.0 m | 45 m | 21.3 MB | 26 MB | 250.0 | 0.2 | 9 | 0 |
| anrg-3 | 5.3 m | 9 m | 9.0 MB | 12 MB | 115.1 | 68.5 | 2 | 1 |
| anrg-1 | 3.9 m | 10 m | 20.2 MB | 22 MB | 96.8 | 61.2 | 2 | 1 |
| anrg-2 | 1.0 m | 1 m | 4.3 MB | 5 MB | 0.0 | 0.0 | 0 | 0 |
| anrg-8 | 10.2 m | 25 m | 28.0 MB | 31 MB | 130.7 | 0.0 | 3 | 0 |
| anrg-4 | 5.1 m | 17 m | 48.2 MB | 55 MB | 257.0 | 115.4 | 2 | 1 |
| anrg-9 | 2.2 m | 4 m | 9.3 MB | 11 MB | 0.2 | 0.0 | 5 | 0 |
| anrg-5 | 6.0 m | 23 m | 48.0 MB | 55 MB | 269.5 | 129.4 | 2 | 1 |
| anrg-6 | 1.7 m | 2 m | 5.7 MB | 7 MB | 0.0 | 0.0 | 0 | 0 |

Aggregate peak across 9 agents: CPU 136 m (0.14 cores), RSS 224 MB. Bounded-fanout invariant: max inflight at any agent 1 (config max = 4).
