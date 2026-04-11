# IMC4 Trading Challenge  
Various codes for the IMC4 Trading Challenge  

## Quick Start
Use a virtual env
```bash
python3 -m venv venv
source venv/bin/activate
pip3 install -m requirements.txt
```
To run your amazing algorithm, we are using [this]() backtester. Follow the instructions to download it, and then run it by 
```bash
prosperity4btx trader.py n
```
for round $n$.
## architectural plans

## datamodel.py
To better understand the data structure of TradeState class, we can utilize a diagram!
```mermaid
graph TD
    %% Source Layer
    subgraph Sources [Data Sources]
        Market((Market Exchange))
        Env((Environment))
    end

    %% State Layer
    subgraph Data_Payload [TradingState]
        TS[TradingState Object]
        
        subgraph Market_Data [Market Data]
            L[Listing]
            OD[OrderDepth]
            MT[Market Trades]
        end
        
        subgraph Internal_Data [Private Data]
            Pos[Position]
            OT[Own Trades]
        end
        
        subgraph Env_Data [Environmental Data]
            Obs[Observation]
            CObs[ConversionObservation]
        end
    end

    %% Processing Layer
    subgraph Bot_Logic [Trading Strategy]
        Bot{Amazing Algorithm}
    end

    %% Action Layer
    subgraph Output [Execution]
        Ord[Order Object]
    end

    %% Connections
    Market -->|Fills| L
    Market -->|Fills| OD
    Market -->|Fills| MT
    
    Env -->|Fills| Obs
    Obs -->|Maps to| CObs
    
    %% Pulling into State
    L & OD & MT & Pos & OT & Obs --> TS
    
    %% Flow to Bot
    TS -->|Full Context| Bot
    
    %% Flow to Market
    Bot -->|Decide What to Order| Ord
    Ord -->|Submission| Market
    
    %% Feedback Loop
    Market -.->|Confirmed Execution| OT
    OT -.->|Updates| Pos

    %% Styling
    style TS fill:#940394,stroke:#333,stroke-width:2px
    style Bot fill:#c90241,stroke:#333,stroke-width:2px
    style Market fill:#0a6302,stroke:#333
    style Env fill:#028bbd,stroke:#cc6600
```
This is all taken from the definition of datamodel.py as is done [here](https://imc-prosperity.notion.site/writing-an-algorithm-in-python) in Appendix B. It should explain the basic game loop. 