# Architecture Overview

ORE Miner V3 separates historical reconstruction, research, strategy logic, and
live execution.

```text
replay -> datasets -> analysis -> models/rules -> strategies -> evaluation
                                                        |
                                                        v
                                              paper/live execution
```

## Boundary Rule

Research-time outcomes may be used to create labels and evaluate performance,
but they may never enter the strategy-visible decision state.

## Production Goal

The architecture must support a miner that is both statistically defensible and
operationally dependable. A profitable backtest with unreliable transactions is
not sufficient, and a reliable miner without demonstrated edge is not
sufficient.
