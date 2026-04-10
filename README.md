# IMC4 Trading Challenge  
Various codes for the IMC4 Trading Challenge  

## Quick Start
Use a virtual env
```bash
python3 -m venv venv
source venv/bin/activate
pip3 install -m requirements.txt
```
  
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
    Bot -->|Calculates Intent| Ord
    Ord -->|Submission| Market
    
    %% Feedback Loop
    Market -.->|Confirmed Execution| OT
    OT -.->|Updates| Pos

    %% Styling
    style TS fill:#f9f,stroke:#333,stroke-width:2px
    style Bot fill:#bbf,stroke:#333,stroke-width:2px
    style Market fill:#dfd,stroke:#333
    style Env fill:#fff2e6,stroke:#cc6600
```