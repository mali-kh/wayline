# Data-agent resource overhead — `overhead-k3.csv`

Time window 221s, 300 samples across 9 agents.

| node | CPU mean | CPU peak | RSS mean | RSS peak | bytes in (MB) | bytes out (MB) | PUT count | peak inflight |
|------|---------:|---------:|---------:|---------:|--------------:|---------------:|----------:|--------------:|
| anrg-7 | 7.0 m | 24 m | 26.6 MB | 27 MB | 50.9 | 4.5 | 12 | 0 |
| anrg-3 | 6.5 m | 31 m | 16.1 MB | 17 MB | 182.4 | 42.5 | 6 | 0 |
| anrg-1 | 5.6 m | 29 m | 26.4 MB | 28 MB | 144.5 | 37.7 | 6 | 0 |
| anrg-2 | 1.0 m | 1 m | 4.3 MB | 5 MB | 0.0 | 0.0 | 0 | 0 |
| anrg-8 | 7.9 m | 26 m | 33.2 MB | 34 MB | 47.5 | 4.1 | 12 | 0 |
| anrg-4 | 8.1 m | 33 m | 63.3 MB | 68 MB | 493.5 | 68.7 | 6 | 2 |
| anrg-9 | 4.9 m | 8 m | 11.7 MB | 12 MB | 0.6 | 0.0 | 15 | 0 |
| anrg-5 | 11.7 m | 70 m | 63.8 MB | 69 MB | 493.7 | 73.4 | 6 | 3 |
| anrg-6 | 18.3 m | 79 m | 11.8 MB | 14 MB | 156.2 | 5.9 | 21 | 0 |

Aggregate peak across 9 agents: CPU 301 m (0.30 cores), RSS 274 MB. Bounded-fanout invariant: max inflight at any agent 3 (config max = 4).
