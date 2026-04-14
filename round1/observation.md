# ROUND 1

Remove NaNs

### Product Analysis Summary: INTARIAN_PEPPER_ROOT
Remove the linear trend
| Day | Slope ($m$) | Intercept ($b$) | % Above Trend | % Below Trend |
| :--- | :--- | :--- | :--- | :--- |
| **Day -2** | 0.1002 | 9999.97 | 50.51% | 49.49% |
| **Day -1** | 0.1002 | 11000.13 | 50.38% | 49.62% |
| **Day 0** | 0.1002 | 12000.17 | 51.03% | 48.97% |
| **Day 1 (MA)** | 0.1002 | 9999.97 | 82.77% | 16.87% |

**Key Insights:**
* **Fixed Drift:** The slope is nearly identical across all three days (~0.1002), indicating a constant upward price pressure.
* **Base Reset:** The intercept increases by 1,000 units exactly each day, suggesting a systematic opening price adjustment.
* **High Symmetry:** The near 50/50 split between above/below trend values confirms the linear detrending is a highly effective model for this product.

### Strategy
```mermaid
graph TD
    Start([Start: TradingState Received]) --> LoadData[Load history from traderData]
    LoadData --> ProductLoop{Loop Each Product}
    
    subgraph Analytics[Analytics Engine]
        ProductLoop --> UpdateHistory[Append Mid-Price to History]
        UpdateHistory --> DetrendChoice{Product Type?}
        DetrendChoice -- ASH_COATED_OSMIUM --> DetrendMA[Detrend: Subtract Window Mean]
        DetrendChoice -- Others --> DetrendLinear[Detrend: Subtract Linear Fit]
        DetrendMA --> CalcStats[Calculate Z-Score & Autocorrelation]
        DetrendLinear --> CalcStats
    end

    CalcStats --> Filters{Pass Filters?}
    
    subgraph SafetyFilters[Risk & Signal Filters]
        Filters --> F1{Standard Dev > 0?}
        F1 -- No --> Skip
        F1 -- Yes --> F2{Slope < Threshold?}
        F2 -- No --> Skip
        F2 -- Yes --> F3{Spread < Max?}
        F3 -- No --> Skip
        F3 -- Yes --> F4{Abs Z-Score > Entry?}
        F4 -- No --> Skip
        F4 -- Yes --> F5{Autocorr < -0.1?}
        F5 -- No --> Skip
    end

    F5 -- Yes --> PosSizing[Calculate Target Position: z / 2.5 * Limit]
    PosSizing --> PassivePrice[Set Prices: Bid+1 / Ask-1]
    
    PassivePrice --> Execution{Delta vs Current Pos}
    Execution -- Delta > 0 --> Buy[Append Buy Order]
    Execution -- Delta < 0 --> Sell[Append Sell Order]
    
    Skip[Skip Trading for Product] --> EndLoop
    Buy --> EndLoop
    Sell --> EndLoop
    
    EndLoop{More Products?}
    EndLoop -- Yes --> ProductLoop
    EndLoop -- No --> SaveData[Serialize history to traderData]
    SaveData --> Return([Return result, conversions, traderData])
```