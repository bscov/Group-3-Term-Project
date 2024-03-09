# Group-3-Term-Project
## Expansion on the Coffee Shop Problem: A Python Discrete Event Simulation
Griffin Arnone, Anhua Cheng, & Bailey Scoville
## Abstract
This research conducts a discrete event simulation of coffee shop operations in a tourism-heavy area. The coffee shop owners aim to maximize revenue while minimizing labor costs and lost revenue due to customers balking and reneging. Using Python, we conduct several simulation experiments to determine optimal staffing levels during three dayparts: morning, afternoon, and evening. We adjust customer behaviors, such as wait time tolerance and average check, to recreate the typical conditions of each daypart. Based on the objective of maximizing revenues, the simulations indicate three baristas should work the morning shift and one barista should work the afternoon and evening shifts. A full discussion of the simulation, methods, and results is included in this [paper](https://github.com/bscov/Group-3-Term-Project/blob/main/Group3_TermProjectPaper.pdf) and summarized in this [presentation](https://github.com/bscov/Group-3-Term-Project/blob/main/Group3_TermProjectSlides.pdf).
## Problem Definition
Objective: Maximize Profits at the coffee shop
Concerns:
- Managing Labor Costs (barista pay $18/hr)
- Lost revenue (from balking and reneging)
- Low wait time tolerance of 30% of customer base
## Methods
We completed the simulation code using Python’s SimPy and Random libraries, among others. We defined functions to recreate the customer experience at the coffee shop, represented by the [event graph](https://github.com/bscov/Group-3-Term-Project/blob/main/Group3_EventGraph.png). 
We divided the simulation into three dayparts (morning, afternoon, and evening) to represent fluctuations in customer arrival rate, average check, and wait time tolerance throughout the day. Additionally, we ran each daypart simulation three times to simulate service with one, two, and three baristas on shift. Python code and output are included in the [code folder](https://github.com/bscov/Group-3-Term-Project/tree/main/Code). 
## Results
The results from the three simulations are included in the [morning shift](https://github.com/bscov/Group-3-Term-Project/blob/main/Results/Group3_MorningShiftResults.png), [afternoon shift](https://github.com/bscov/Group-3-Term-Project/blob/main/Results/Group3_AfternoonShiftResults.png), and [evening shift](https://github.com/bscov/Group-3-Term-Project/blob/main/Results/Group3_EveningShiftResults.png) tables. The simulation with the best profit outcome was a morning shift staffed by three baristas. 
## Management Recommendations
Based on the outcomes of the three simulations, we recommend:
- Three baristas on staff in the morning, one in the afternoon, one in the evening
- Optimize barista workflows and training for efficiency to lower wait times
- Implement a pre-order option to reduce wait times
- Expand product offering to incentivize off-peak visits in the afternoon and evening
