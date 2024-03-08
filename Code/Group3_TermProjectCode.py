#!/usr/bin/env python
# coding: utf-8

# In[64]:


#import libraries
import simpy
import wraps
import numpy as np
import pandas as pd
import queue
import random
from functools import partial, wraps

#set display preferences
pd.set_option('display.max_rows', 20)
pd.set_option('display.max_columns', 10)

# Set up notebook to display multiple outputs in one cell
from IPython.core.interactiveshell import InteractiveShell
InteractiveShell.ast_node_interactivity = "all"


# # Coffee Shop Simulation Test

# ## Define Staffing, Wait, Balking, Reneging

# In[65]:


#define number of baristas 
baristas = 1

#define service times (in minutes)
min_service_time = 1
mean_service_time = 2
max_service_time = 5

#define reneging wait time (in minutes)
max_wait_time = 10

#define arrival pace (in minutes)
mean_inter_arrival_time = 1

#define balking tolerance (number of people in line)
balk_queue_length = 6


# In[66]:


#enable reproducible results
obtain_reproducible_results = True

#set simulation parameters
sim_hours = 10
fixed_sim_time = sim_hours * 60 * 60 #convert hours to seconds 

#create parameter strings
parameter_strings_list = [str(sim_hours), 'hours',
                         str(baristas), str(min_service_time),
                         str(mean_service_time), str(max_service_time),
                         str(mean_inter_arrival_time), str(balk_queue_length), str(max_wait_time)]
separator = '-'
simulation_file_identifier = separator.join(parameter_strings_list)


# ## Define Simulation Functions

# In[67]:


#create function for random service times
def random_service_time(min_service_time, mean_service_time, max_service_time) :
    try_service_time = np.random.exponential(scale = mean_service_time)
    if (try_service_time < min_service_time):
        return(min_service_time)
    if (try_service_time > max_service_time):
        return(max_service_time)
    if (try_service_time >= min_service_time) and (try_service_time <= max_service_time):
        return(try_service_time)


# In[68]:


#create function for random arrivals and balking condition
def arrival(env, caseid, caseid_queue, event_log):
    caseid = 0
    while True:  
        inter_arrival_time = round(60*np.random.exponential(scale = mean_inter_arrival_time))
        print("Next arrival time: ", env.now + inter_arrival_time)
        yield env.timeout(inter_arrival_time)  
        caseid += 1
        time = env.now
        activity = 'arrival'
        env.process(event_log_append(env, caseid, time, activity, event_log)) 
        yield env.timeout(0) 
        if caseid_queue.qsize() < balk_queue_length:
            caseid_queue.put(caseid)          
            print("Customer joins queue --> caseid =",caseid,', time = ',env.now,', queue_length =',caseid_queue.qsize())
            time = env.now
            activity = 'join_queue'
            env.process(event_log_append(env, caseid, time, activity, event_log)) 
            env.process(service_process(env,  caseid_queue, event_log))       
        else:
            print("Customer balks --> caseid =",caseid,', time = ',env.now,', queue_length =',caseid_queue.qsize()) 
            env.process(event_log_append(env, caseid, env.now, 'balk', event_log)) 


# In[69]:


#create function for flow of service and renege condition and number of baristas
def service_process(env, caseid_queue, event_log):
    with baristas_on_shift.request() as req:
        yield req  
        if not caseid_queue.empty():
            queue_length_on_entering_service = caseid_queue.qsize()
            caseid = caseid_queue.get()
            wait_time = env.now - queue_length_on_entering_service * (mean_service_time * 60)
            if wait_time > (max_wait_time * 60) and random.random() <= 0.3:
                print("Customer", caseid, 'left the queue after waiting for', wait_time, 'minutes')
                env.process(event_log_append(env, caseid, env.now, 'renege', event_log))
            else:
                #adjusts service time based on # of baristas working
                adjusted_mean_service_time = mean_service_time / baristas
                adjusted_max_service_time = max_service_time / baristas
                print("Begin_service --> caseid =",caseid,', time = ',env.now,', queue_length =', queue_length_on_entering_service)
                env.process(event_log_append(env, caseid, env.now, 'begin_service', event_log)) 
                service_time = round(60*random_service_time(min_service_time, mean_service_time, max_service_time))   
                yield env.timeout(service_time) 
                queue_length_on_leaving_service = caseid_queue.qsize()
                print("End_service --> caseid =",caseid,', time = ',env.now,', queue_length =', queue_length_on_leaving_service)
                env.process(event_log_append(env, caseid, env.now, 'end_service', event_log))


# In[70]:


#create function to process events
def trace(env, callback):
    def get_wrapper(env_step, callback):
        @wraps(env_step)
        def tracing_step():
            if len(env._queue):
                t, prio, eid, event = env._queue[0]
                callback(t, prio, eid, event)
            return env_step()
        return tracing_step
        
    env.step = get_wrapper(env.step, callback)

def trace_monitor(data, t, prio, eid, event):
    data.append((t, eid, type(event)))
    
def test_process(env):
    yield env.timeout(1)


# In[71]:


#create function for creating log
def event_log_append(env, caseid, time, activity, event_log):
    event_log.append((caseid, time, activity))
    yield env.timeout(0)


# ## Simulation Test

# In[72]:


#set random seed
if obtain_reproducible_results:
    np.random.seed(9876)
    
#set simulation trace monitoring
simulation_data = []
this_trace_monitor = partial(trace_monitor, simulation_data)

env = simpy.Environment()
trace(env, this_trace_monitor)

env.process(test_process(env))

#set FIFO queue for caseid values
caseid_queue = queue.Queue()

#set limits on baristas resource
baristas_on_shift = simpy.Resource(env, capacity = baristas)
caseid = -1

#create event log tuple
event_log = [(caseid, 0, 'null_start_simulation')]
env.process(event_log_append(env, caseid, env.now, 'start_simulation', event_log))

#call customer arrival generator to start simulation
env.process(arrival(env, caseid, caseid_queue, event_log))

env.run(until = fixed_sim_time)


# In[73]:


#create text file for simulation output
simulation_trace_file_name = 'simulation-program-trace-' + simulation_file_identifier + '.txt'
with open(simulation_trace_file_name, 'wt') as ftrace:
    for d in simulation_data:
        print(str(d), file = ftrace)
print()        
print('simulation program trace written to file:',simulation_trace_file_name)

# convert list of tuples to list of lists
event_log_list = [list(element) for element in event_log]

# convert to pandas data frame
caseid_list = []
time_list = []
activity_list = []
for d in event_log_list:
    if d[0] > 0:
        caseid_list.append(d[0])
        time_list.append(d[1])
        activity_list.append(d[2])
event_log_df = pd.DataFrame({'caseid':caseid_list,
                             'time':time_list,
                             'activity':activity_list})

#save event log to CSV file
event_log_file_name = 'simulation-event-log-' + simulation_file_identifier + '.csv'
event_log_df.to_csv(event_log_file_name, index = False)
print()
print('event log written to file:',event_log_file_name)


# In[74]:


#inspect event log
event_log_df.head()


# ## Simulation Summary and Summary Statistics

# In[75]:


avg_ticket = 5
sim_revenue = (len(event_log_df['activity'][event_log_df['activity']=='end_service']) * avg_ticket)
lost_revenue = (len(event_log_df['activity'][event_log_df['activity']=='balk']) * avg_ticket) + (len(event_log_df['activity'][event_log_df['activity']=='renege']) * avg_ticket)
barista_wages = 18 #per hour
sim_payroll = baristas * barista_wages * sim_hours

#print simulation results
print()
print('Simulation parameter settings:')
print(baristas, 'baristas/servers')
print('  Service time settings (in minutes)')
print('    minimum:',min_service_time)
print('    mean:   ',mean_service_time)
print('    maximum:',max_service_time)
print()
print('Customers set to arrive every', mean_inter_arrival_time, 'minute(s) on average')
print('Customers will not join the queue/waiting line if it has',balk_queue_length, 'customers in it (balking)')
print('Customers will leave the queue/waiting line after waiting', max_wait_time, 'minute(s) (reneging)' )
print('The simulation is set to run for ', sim_hours,' hours (',60 * sim_hours,' minutes)', sep ='')
print()
end_time = np.max(event_log_df["time"])
print('Results after ',end_time, ' seconds (', round(end_time/60, 2), ' minutes, ',round(end_time/(60*60),2),' hours):', sep = '')
caseid_list = pd.unique(event_log_df['caseid'])
print(len(caseid_list), 'unique customers arrived')
print(len(event_log_df['activity'][event_log_df['activity']=='join_queue']),'customers joined the queue for service')
print(len(event_log_df['activity'][event_log_df['activity']=='balk']),'customers balked (lost business)')
print(len(event_log_df['activity'][event_log_df['activity']=='renege']),'customers reneged (left queue, lost business)')
print(len(event_log_df['activity'][event_log_df['activity']=='begin_service']),'customers began service')
print(len(event_log_df['activity'][event_log_df['activity']=='end_service']),'customers ended service')
print(caseid_queue.qsize(),'customers were still in line at the end of the simulation')
print()
print(f'${sim_revenue:.2f} average simulation revenue (assuming ${avg_ticket} average ticket)')
print(f'${lost_revenue:.2f} average lost revenue (balking & reneging)')
print(f'${sim_payroll:.2f} simulation payroll costs')

# case-by-case logs are very useful for checking the logic of the simulation
case_by_case_event_file_name = 'simulation-program-case-by-case-events-' + simulation_file_identifier + '.txt'
with open(case_by_case_event_file_name, 'wt') as fcasedata:
    lastcase_arrival_time = 0  # initialize for use with first case
    # create lists for storing time interval data 
    inter_arrival_times = [] # computed across cases
    waiting_time = [] # computed within each case that has begun service
    service_time = [] # computed within each case that has ended service
    for thiscase in caseid_list:
        # select subset of rows for thiscase and use as a Pandas data frame
        thiscase_events = event_log_df[['caseid','time','activity']][event_log_df['caseid']==thiscase]
        print(file = fcasedata)
        print('events for caseid',thiscase, file = fcasedata)
        print(thiscase_events, file = fcasedata) 
        # compute inter-arrival times between cases
        thiscase_arrival_time = thiscase_events.loc[thiscase_events['activity']=='arrival', 'time'].values[0]
        inter_arrival_time = thiscase_arrival_time - lastcase_arrival_time
        inter_arrival_times.append(inter_arrival_time)
        print(file = fcasedata)
        print('time between arrivals (this case minus previous case):',inter_arrival_time, 'seconds', file = fcasedata)
        lastcase_arrival_time  = thiscase_arrival_time # save for next case in the for-loop
        # compute waiting times within this case (must have begin_service event/activity)
        if thiscase_events.loc[thiscase_events['activity']=='begin_service'].shape[0] == 1:
            thiscase_begin_service = thiscase_events.loc[thiscase_events['activity']=='begin_service', 'time'].values[0]
            thiscase_join_queue = thiscase_arrival_time = thiscase_events.loc[thiscase_events['activity']=='join_queue', 'time'].values[0]
            thiscase_waiting_time = thiscase_begin_service - thiscase_join_queue
            waiting_time.append(thiscase_waiting_time)
            print('waiting time for this case (time between joining queue and beginning service):',thiscase_waiting_time, 'seconds', file = fcasedata)
        # compute service time within this case (must have end_service event/activity)
        if thiscase_events.loc[thiscase_events['activity']=='end_service'].shape[0] == 1:
            thiscase_end_service = thiscase_events.loc[thiscase_events['activity']=='end_service', 'time'].values[0]
            thiscase_service_time = thiscase_end_service - thiscase_begin_service
            service_time.append(thiscase_service_time)
            print('service time for this case (time between beginning and ending service):',thiscase_service_time, 'seconds', file = fcasedata)
        
print()     
print('Summary statistics for customer inter-arrival times:')
print('  Minimum: ',round(np.min(inter_arrival_times),2), ' seconds (' ,round(np.min(inter_arrival_times)/60,2), ' minutes)',sep='')  
print('  Mean:    ',round(np.average(inter_arrival_times),2), ' seconds (' ,round(np.average(inter_arrival_times)/60,2), ' minutes)',sep='')  
print('  Maximum: ',round(np.max(inter_arrival_times),2), ' seconds (' ,round(np.max(inter_arrival_times)/60,2), ' minutes)',sep='')      
print()
print('Summary statistics for customer wait times:')
print('  Minimum: ',round(np.min(waiting_time),2), ' seconds (' ,round(np.min(waiting_time)/60,2), ' minutes)',sep='')  
print('  Mean:    ',round(np.average(waiting_time),2), ' seconds (' ,round(np.average(waiting_time)/60,2), ' minutes)',sep='')  
print('  Maximum: ',round(np.max(waiting_time),2), ' seconds (' ,round(np.max(waiting_time)/60,2), ' minutes)',sep='')  
print()
print('Summary statistics for service times:')
print('  Minimum: ',round(np.min(service_time),2), ' seconds (' ,round(np.min(service_time)/60,2), ' minutes)',sep='')  
print('  Mean:    ',round(np.average(service_time),2), ' seconds (' ,round(np.average(service_time)/60,2), ' minutes)',sep='')  
print('  Maximum: ',round(np.max(service_time),2), ' seconds (' ,round(np.max(service_time)/60,2), ' minutes)',sep='')  


# ## Observations:
# 
# From the simulation test, we determine more baristas are needed to meet the flow of new customers as at the set inter arrival time of 1 minute. Maximum wait time of 18.3 minutes far exceeded the 10 minute wait tolerance of 30% of customer base.

# # Morning Shift Simulation 6-10 A.M.

# ## Define Staffing, Wait, Balking, Reneging

# In[76]:


#define staff 
baristas = 3

#define service times (in minutes)
min_service_time = 1
mean_service_time = 2
max_service_time = 5

#define wait times (in minutes)
max_wait_time = 10

#define arrival pace (in minutes)
mean_inter_arrival_time = 1

#define balking tolerance (number of people in line)
balk_queue_length = 10


# In[77]:


#enable reproducible results
obtain_reproducible_results = True

#set simulation parameters 
sim_hours = 4
fixed_sim_time = sim_hours * 60 * 60 #convert hours to seconds 

#create parameter strings
parameter_strings_list = [str(sim_hours), 'hours',
                         str(baristas), str(min_service_time),
                         str(mean_service_time), str(max_service_time),
                         str(mean_inter_arrival_time), str(balk_queue_length), str(max_wait_time)]
separator = '-'
simulation_file_identifier = separator.join(parameter_strings_list)


# In[78]:


#set random seed
if obtain_reproducible_results:
    np.random.seed(9876)
    
#set simulation trace monitoring
simulation_data = []
this_trace_monitor = partial(trace_monitor, simulation_data)

env = simpy.Environment()
trace(env, this_trace_monitor)

env.process(test_process(env))

#set FIFO queue for caseid values
caseid_queue = queue.Queue()

#set limits on baristas resource
baristas_on_shift = simpy.Resource(env, capacity = baristas)
caseid = -1

#create event log tuple
event_log = [(caseid, 0, 'null_start_simulation')]
env.process(event_log_append(env, caseid, env.now, 'start_simulation', event_log))

#call customer arrival generator to start simulation
env.process(arrival(env, caseid, caseid_queue, event_log))

env.run(until = fixed_sim_time)


# In[79]:


#create text file for simulation output
simulation_trace_file_name = 'simulation-program-trace-' + simulation_file_identifier + '.txt'
with open(simulation_trace_file_name, 'wt') as ftrace:
    for d in simulation_data:
        print(str(d), file = ftrace)
print()        
print('simulation program trace written to file:',simulation_trace_file_name)

# convert list of tuples to list of lists
event_log_list = [list(element) for element in event_log]

# convert to pandas data frame
caseid_list = []
time_list = []
activity_list = []
for d in event_log_list:
    if d[0] > 0:
        caseid_list.append(d[0])
        time_list.append(d[1])
        activity_list.append(d[2])
event_log_df = pd.DataFrame({'caseid':caseid_list,
                             'time':time_list,
                             'activity':activity_list})

#save event log to CSV file
event_log_file_name = 'simulation-event-log-' + simulation_file_identifier + '.csv'
event_log_df.to_csv(event_log_file_name, index = False)
print()
print('event log written to file:',event_log_file_name)


# In[80]:


event_log_df.head()


# In[81]:


avg_ticket = 10
sim_revenue = (len(event_log_df['activity'][event_log_df['activity']=='end_service']) * avg_ticket)
lost_revenue = (len(event_log_df['activity'][event_log_df['activity']=='balk']) * avg_ticket) + (len(event_log_df['activity'][event_log_df['activity']=='renege']) * avg_ticket)
barista_wages = 18 #per hour
sim_payroll = baristas * barista_wages* sim_hours

#print simulation results
print()
print('Simulation parameter settings:')
print(baristas, 'baristas/servers')
print('  Service time settings (in minutes)')
print('    minimum:',min_service_time)
print('    mean:   ',mean_service_time)
print('    maximum:',max_service_time)
print()
print('Customers set to arrive every', mean_inter_arrival_time, 'minute(s) on average')
print('Customers will not join the queue/waiting line if it has',balk_queue_length, 'customers in it (balking)')
print('Customers will leave the queue/waiting line after waiting', max_wait_time, 'minute(s) (reneging)' )
print('The simulation is set to run for ', sim_hours,' hours (',60 * sim_hours,' minutes)', sep ='')
print()
end_time = np.max(event_log_df["time"])
print('Results after ',end_time, ' seconds (', round(end_time/60, 2), ' minutes, ',round(end_time/(60*60),2),' hours):', sep = '')
caseid_list = pd.unique(event_log_df['caseid'])
print(len(caseid_list), 'unique customers arrived')
print(len(event_log_df['activity'][event_log_df['activity']=='join_queue']),'customers joined the queue for service')
print(len(event_log_df['activity'][event_log_df['activity']=='balk']),'customers balked (lost business)')
print(len(event_log_df['activity'][event_log_df['activity']=='renege']),'customers reneged (left queue, lost business)')
print(len(event_log_df['activity'][event_log_df['activity']=='begin_service']),'customers began service')
print(len(event_log_df['activity'][event_log_df['activity']=='end_service']),'customers ended service')
print(caseid_queue.qsize(),'customers were still in line at the end of the simulation')
print()
print(f'${sim_revenue:.2f} average simulation revenue (assuming ${avg_ticket} average ticket)')
print(f'${lost_revenue:.2f} average lost revenue (balking & reneging)')
print(f'${sim_payroll:.2f} simulation payroll costs')

# case-by-case logs are very useful for checking the logic of the simulation
case_by_case_event_file_name = 'simulation-program-case-by-case-events-' + simulation_file_identifier + '.txt'
with open(case_by_case_event_file_name, 'wt') as fcasedata:
    lastcase_arrival_time = 0  # initialize for use with first case
    # create lists for storing time interval data 
    inter_arrival_times = [] # computed across cases
    waiting_time = [] # computed within each case that has begun service
    service_time = [] # computed within each case that has ended service
    for thiscase in caseid_list:
        # select subset of rows for thiscase and use as a Pandas data frame
        thiscase_events = event_log_df[['caseid','time','activity']][event_log_df['caseid']==thiscase]
        print(file = fcasedata)
        print('events for caseid',thiscase, file = fcasedata)
        print(thiscase_events, file = fcasedata) 
        # compute inter-arrival times between cases
        thiscase_arrival_time = thiscase_events.loc[thiscase_events['activity']=='arrival', 'time'].values[0]
        inter_arrival_time = thiscase_arrival_time - lastcase_arrival_time
        inter_arrival_times.append(inter_arrival_time)
        print(file = fcasedata)
        print('time between arrivals (this case minus previous case):',inter_arrival_time, 'seconds', file = fcasedata)
        lastcase_arrival_time  = thiscase_arrival_time # save for next case in the for-loop
        # compute waiting times within this case (must have begin_service event/activity)
        if thiscase_events.loc[thiscase_events['activity']=='begin_service'].shape[0] == 1:
            thiscase_begin_service = thiscase_events.loc[thiscase_events['activity']=='begin_service', 'time'].values[0]
            thiscase_join_queue = thiscase_arrival_time = thiscase_events.loc[thiscase_events['activity']=='join_queue', 'time'].values[0]
            thiscase_waiting_time = thiscase_begin_service - thiscase_join_queue
            waiting_time.append(thiscase_waiting_time)
            print('waiting time for this case (time between joining queue and beginning service):',thiscase_waiting_time, 'seconds', file = fcasedata)
        # compute service time within this case (must have end_service event/activity)
        if thiscase_events.loc[thiscase_events['activity']=='end_service'].shape[0] == 1:
            thiscase_end_service = thiscase_events.loc[thiscase_events['activity']=='end_service', 'time'].values[0]
            thiscase_service_time = thiscase_end_service - thiscase_begin_service
            service_time.append(thiscase_service_time)
            print('service time for this case (time between beginning and ending service):',thiscase_service_time, 'seconds', file = fcasedata)
        
print()     
print('Summary statistics for customer inter-arrival times:')
print('  Minimum: ',round(np.min(inter_arrival_times),2), ' seconds (' ,round(np.min(inter_arrival_times)/60,2), ' minutes)',sep='')  
print('  Mean:    ',round(np.average(inter_arrival_times),2), ' seconds (' ,round(np.average(inter_arrival_times)/60,2), ' minutes)',sep='')  
print('  Maximum: ',round(np.max(inter_arrival_times),2), ' seconds (' ,round(np.max(inter_arrival_times)/60,2), ' minutes)',sep='')      
print()
print('Summary statistics for customer wait times:')
print('  Minimum: ',round(np.min(waiting_time),2), ' seconds (' ,round(np.min(waiting_time)/60,2), ' minutes)',sep='')  
print('  Mean:    ',round(np.average(waiting_time),2), ' seconds (' ,round(np.average(waiting_time)/60,2), ' minutes)',sep='')  
print('  Maximum: ',round(np.max(waiting_time),2), ' seconds (' ,round(np.max(waiting_time)/60,2), ' minutes)',sep='')  
print()
print('Summary statistics for service times:')
print('  Minimum: ',round(np.min(service_time),2), ' seconds (' ,round(np.min(service_time)/60,2), ' minutes)',sep='')  
print('  Mean:    ',round(np.average(service_time),2), ' seconds (' ,round(np.average(service_time)/60,2), ' minutes)',sep='')  
print('  Maximum: ',round(np.max(service_time),2), ' seconds (' ,round(np.max(service_time)/60,2), ' minutes)',sep='')  


# # Afternoon Shift Simulation 10 A.M. - 2 P.M.

# ## Define Staffing, Wait, Balking, Reneging

# In[82]:


#define staff 
baristas = 2

#define service times (in minutes)
min_service_time = 1
mean_service_time = 2
max_service_time = 5

#define wait times (in minutes)
max_wait_time = 6

#define arrival pace (in minutes)
mean_inter_arrival_time = 5

#define balking tolerance (number of people in line)
balk_queue_length = 6


# In[83]:


#enable reproducible results
obtain_reproducible_results = True

#set simulation parameters 
sim_hours = 4
fixed_sim_time = sim_hours * 60 * 60 #convert hours to seconds 

#create parameter strings
parameter_strings_list = [str(sim_hours), 'hours',
                         str(baristas), str(min_service_time),
                         str(mean_service_time), str(max_service_time),
                         str(mean_inter_arrival_time), str(balk_queue_length), str(max_wait_time)]
separator = '-'
simulation_file_identifier = separator.join(parameter_strings_list)


# In[84]:


#set random seed
if obtain_reproducible_results:
    np.random.seed(9876)
    
#set simulation trace monitoring
simulation_data = []
this_trace_monitor = partial(trace_monitor, simulation_data)

env = simpy.Environment()
trace(env, this_trace_monitor)

env.process(test_process(env))

#set FIFO queue for caseid values
caseid_queue = queue.Queue()

#set limits on baristas resource
baristas_on_shift = simpy.Resource(env, capacity = baristas)
caseid = -1

#create event log tuple
event_log = [(caseid, 0, 'null_start_simulation')]
env.process(event_log_append(env, caseid, env.now, 'start_simulation', event_log))

#call customer arrival generator to start simulation
env.process(arrival(env, caseid, caseid_queue, event_log))

env.run(until = fixed_sim_time)


# In[85]:


#create text file for simulation output
simulation_trace_file_name = 'simulation-program-trace-' + simulation_file_identifier + '.txt'
with open(simulation_trace_file_name, 'wt') as ftrace:
    for d in simulation_data:
        print(str(d), file = ftrace)
print()        
print('simulation program trace written to file:',simulation_trace_file_name)

# convert list of tuples to list of lists
event_log_list = [list(element) for element in event_log]

# convert to pandas data frame
caseid_list = []
time_list = []
activity_list = []
for d in event_log_list:
    if d[0] > 0:
        caseid_list.append(d[0])
        time_list.append(d[1])
        activity_list.append(d[2])
event_log_df = pd.DataFrame({'caseid':caseid_list,
                             'time':time_list,
                             'activity':activity_list})

#save event log to CSV file
event_log_file_name = 'simulation-event-log-' + simulation_file_identifier + '.csv'
event_log_df.to_csv(event_log_file_name, index = False)
print()
print('event log written to file:',event_log_file_name)


# In[86]:


event_log_df.head()


# In[87]:


avg_ticket = 5
sim_revenue = (len(event_log_df['activity'][event_log_df['activity']=='end_service']) * avg_ticket)
lost_revenue = (len(event_log_df['activity'][event_log_df['activity']=='balk']) * avg_ticket) + (len(event_log_df['activity'][event_log_df['activity']=='renege']) * avg_ticket)
barista_wages = 18 #per hour
sim_payroll = baristas * barista_wages* sim_hours

#print simulation results
print()
print('Simulation parameter settings:')
print(baristas, 'baristas/servers')
print('  Service time settings (in minutes)')
print('    minimum:',min_service_time)
print('    mean:   ',mean_service_time)
print('    maximum:',max_service_time)
print()
print('Customers set to arrive every', mean_inter_arrival_time, 'minute(s) on average')
print('Customers will not join the queue/waiting line if it has',balk_queue_length, 'customers in it (balking)')
print('Customers will leave the queue/waiting line after waiting', max_wait_time, 'minute(s) (reneging)' )
print('The simulation is set to run for ', sim_hours,' hours (',60 * sim_hours,' minutes)', sep ='')
print()
end_time = np.max(event_log_df["time"])
print('Results after ',end_time, ' seconds (', round(end_time/60, 2), ' minutes, ',round(end_time/(60*60),2),' hours):', sep = '')
caseid_list = pd.unique(event_log_df['caseid'])
print(len(caseid_list), 'unique customers arrived')
print(len(event_log_df['activity'][event_log_df['activity']=='join_queue']),'customers joined the queue for service')
print(len(event_log_df['activity'][event_log_df['activity']=='balk']),'customers balked (lost business)')
print(len(event_log_df['activity'][event_log_df['activity']=='renege']),'customers reneged (left queue, lost business)')
print(len(event_log_df['activity'][event_log_df['activity']=='begin_service']),'customers began service')
print(len(event_log_df['activity'][event_log_df['activity']=='end_service']),'customers ended service')
print(caseid_queue.qsize(),'customers were still in line at the end of the simulation')
print()
print(f'${sim_revenue:.2f} average simulation revenue (assuming ${avg_ticket} average ticket)')
print(f'${lost_revenue:.2f} average lost revenue (balking & reneging)')
print(f'${sim_payroll:.2f} simulation payroll costs')

# case-by-case logs are very useful for checking the logic of the simulation
case_by_case_event_file_name = 'simulation-program-case-by-case-events-' + simulation_file_identifier + '.txt'
with open(case_by_case_event_file_name, 'wt') as fcasedata:
    lastcase_arrival_time = 0  # initialize for use with first case
    # create lists for storing time interval data 
    inter_arrival_times = [] # computed across cases
    waiting_time = [] # computed within each case that has begun service
    service_time = [] # computed within each case that has ended service
    for thiscase in caseid_list:
        # select subset of rows for thiscase and use as a Pandas data frame
        thiscase_events = event_log_df[['caseid','time','activity']][event_log_df['caseid']==thiscase]
        print(file = fcasedata)
        print('events for caseid',thiscase, file = fcasedata)
        print(thiscase_events, file = fcasedata) 
        # compute inter-arrival times between cases
        thiscase_arrival_time = thiscase_events.loc[thiscase_events['activity']=='arrival', 'time'].values[0]
        inter_arrival_time = thiscase_arrival_time - lastcase_arrival_time
        inter_arrival_times.append(inter_arrival_time)
        print(file = fcasedata)
        print('time between arrivals (this case minus previous case):',inter_arrival_time, 'seconds', file = fcasedata)
        lastcase_arrival_time  = thiscase_arrival_time # save for next case in the for-loop
        # compute waiting times within this case (must have begin_service event/activity)
        if thiscase_events.loc[thiscase_events['activity']=='begin_service'].shape[0] == 1:
            thiscase_begin_service = thiscase_events.loc[thiscase_events['activity']=='begin_service', 'time'].values[0]
            thiscase_join_queue = thiscase_arrival_time = thiscase_events.loc[thiscase_events['activity']=='join_queue', 'time'].values[0]
            thiscase_waiting_time = thiscase_begin_service - thiscase_join_queue
            waiting_time.append(thiscase_waiting_time)
            print('waiting time for this case (time between joining queue and beginning service):',thiscase_waiting_time, 'seconds', file = fcasedata)
        # compute service time within this case (must have end_service event/activity)
        if thiscase_events.loc[thiscase_events['activity']=='end_service'].shape[0] == 1:
            thiscase_end_service = thiscase_events.loc[thiscase_events['activity']=='end_service', 'time'].values[0]
            thiscase_service_time = thiscase_end_service - thiscase_begin_service
            service_time.append(thiscase_service_time)
            print('service time for this case (time between beginning and ending service):',thiscase_service_time, 'seconds', file = fcasedata)
        
print()     
print('Summary statistics for customer inter-arrival times:')
print('  Minimum: ',round(np.min(inter_arrival_times),2), ' seconds (' ,round(np.min(inter_arrival_times)/60,2), ' minutes)',sep='')  
print('  Mean:    ',round(np.average(inter_arrival_times),2), ' seconds (' ,round(np.average(inter_arrival_times)/60,2), ' minutes)',sep='')  
print('  Maximum: ',round(np.max(inter_arrival_times),2), ' seconds (' ,round(np.max(inter_arrival_times)/60,2), ' minutes)',sep='')      
print()
print('Summary statistics for customer wait times:')
print('  Minimum: ',round(np.min(waiting_time),2), ' seconds (' ,round(np.min(waiting_time)/60,2), ' minutes)',sep='')  
print('  Mean:    ',round(np.average(waiting_time),2), ' seconds (' ,round(np.average(waiting_time)/60,2), ' minutes)',sep='')  
print('  Maximum: ',round(np.max(waiting_time),2), ' seconds (' ,round(np.max(waiting_time)/60,2), ' minutes)',sep='')  
print()
print('Summary statistics for service times:')
print('  Minimum: ',round(np.min(service_time),2), ' seconds (' ,round(np.min(service_time)/60,2), ' minutes)',sep='')  
print('  Mean:    ',round(np.average(service_time),2), ' seconds (' ,round(np.average(service_time)/60,2), ' minutes)',sep='')  
print('  Maximum: ',round(np.max(service_time),2), ' seconds (' ,round(np.max(service_time)/60,2), ' minutes)',sep='')  


# # Evening Shift Simulation 2 - 6 P.M.

# ## Define Staffing, Wait, Balking, Reneging

# In[88]:


#define staff 
baristas = 2

#define service times (in minutes)
min_service_time = 1
mean_service_time = 2
max_service_time = 5

#define wait times (in minutes)
max_wait_time = 6

#define arrival pace (in minutes)
mean_inter_arrival_time = 10

#define balking tolerance (number of people in line)
balk_queue_length = 6


# In[89]:


#enable reproducible results
obtain_reproducible_results = True

#set simulation parameters 
sim_hours = 4
fixed_sim_time = sim_hours * 60 * 60 #convert hours to seconds 

#create parameter strings
parameter_strings_list = [str(sim_hours), 'hours',
                         str(baristas), str(min_service_time),
                         str(mean_service_time), str(max_service_time),
                         str(mean_inter_arrival_time), str(balk_queue_length), str(max_wait_time)]
separator = '-'
simulation_file_identifier = separator.join(parameter_strings_list)


# In[90]:


#set random seed
if obtain_reproducible_results:
    np.random.seed(9876)
    
#set simulation trace monitoring
simulation_data = []
this_trace_monitor = partial(trace_monitor, simulation_data)

env = simpy.Environment()
trace(env, this_trace_monitor)

env.process(test_process(env))

#set FIFO queue for caseid values
caseid_queue = queue.Queue()

#set limits on baristas resource
baristas_on_shift = simpy.Resource(env, capacity = baristas)
caseid = -1

#create event log tuple
event_log = [(caseid, 0, 'null_start_simulation')]
env.process(event_log_append(env, caseid, env.now, 'start_simulation', event_log))

#call customer arrival generator to start simulation
env.process(arrival(env, caseid, caseid_queue, event_log))

env.run(until = fixed_sim_time)


# In[91]:


#create text file for simulation output
simulation_trace_file_name = 'simulation-program-trace-' + simulation_file_identifier + '.txt'
with open(simulation_trace_file_name, 'wt') as ftrace:
    for d in simulation_data:
        print(str(d), file = ftrace)
print()        
print('simulation program trace written to file:',simulation_trace_file_name)

# convert list of tuples to list of lists
event_log_list = [list(element) for element in event_log]

# convert to pandas data frame
caseid_list = []
time_list = []
activity_list = []
for d in event_log_list:
    if d[0] > 0:
        caseid_list.append(d[0])
        time_list.append(d[1])
        activity_list.append(d[2])
event_log_df = pd.DataFrame({'caseid':caseid_list,
                             'time':time_list,
                             'activity':activity_list})

#save event log to CSV file
event_log_file_name = 'simulation-event-log-' + simulation_file_identifier + '.csv'
event_log_df.to_csv(event_log_file_name, index = False)
print()
print('event log written to file:',event_log_file_name)


# In[92]:


event_log_df.head()


# In[93]:


avg_ticket = 5
sim_revenue = (len(event_log_df['activity'][event_log_df['activity']=='end_service']) * avg_ticket)
lost_revenue = (len(event_log_df['activity'][event_log_df['activity']=='balk']) * avg_ticket) + (len(event_log_df['activity'][event_log_df['activity']=='renege']) * avg_ticket)
barista_wages = 18 #per hour
sim_payroll = baristas * barista_wages* sim_hours

#print simulation results
print()
print('Simulation parameter settings:')
print(baristas, 'baristas/servers')
print('  Service time settings (in minutes)')
print('    minimum:',min_service_time)
print('    mean:   ',mean_service_time)
print('    maximum:',max_service_time)
print()
print('Customers set to arrive every', mean_inter_arrival_time, 'minute(s) on average')
print('Customers will not join the queue/waiting line if it has',balk_queue_length, 'customers in it (balking)')
print('Customers will leave the queue/waiting line after waiting', max_wait_time, 'minute(s) (reneging)' )
print('The simulation is set to run for ', sim_hours,' hours (',60 * sim_hours,' minutes)', sep ='')
print()
end_time = np.max(event_log_df["time"])
print('Results after ',end_time, ' seconds (', round(end_time/60, 2), ' minutes, ',round(end_time/(60*60),2),' hours):', sep = '')
caseid_list = pd.unique(event_log_df['caseid'])
print(len(caseid_list), 'unique customers arrived')
print(len(event_log_df['activity'][event_log_df['activity']=='join_queue']),'customers joined the queue for service')
print(len(event_log_df['activity'][event_log_df['activity']=='balk']),'customers balked (lost business)')
print(len(event_log_df['activity'][event_log_df['activity']=='renege']),'customers reneged (left queue, lost business)')
print(len(event_log_df['activity'][event_log_df['activity']=='begin_service']),'customers began service')
print(len(event_log_df['activity'][event_log_df['activity']=='end_service']),'customers ended service')
print(caseid_queue.qsize(),'customers were still in line at the end of the simulation')
print()
print(f'${sim_revenue:.2f} average simulation revenue (assuming ${avg_ticket} average ticket)')
print(f'${lost_revenue:.2f} average lost revenue (balking & reneging)')
print(f'${sim_payroll:.2f} simulation payroll costs')

# case-by-case logs are very useful for checking the logic of the simulation
case_by_case_event_file_name = 'simulation-program-case-by-case-events-' + simulation_file_identifier + '.txt'
with open(case_by_case_event_file_name, 'wt') as fcasedata:
    lastcase_arrival_time = 0  # initialize for use with first case
    # create lists for storing time interval data 
    inter_arrival_times = [] # computed across cases
    waiting_time = [] # computed within each case that has begun service
    service_time = [] # computed within each case that has ended service
    for thiscase in caseid_list:
        # select subset of rows for thiscase and use as a Pandas data frame
        thiscase_events = event_log_df[['caseid','time','activity']][event_log_df['caseid']==thiscase]
        print(file = fcasedata)
        print('events for caseid',thiscase, file = fcasedata)
        print(thiscase_events, file = fcasedata) 
        # compute inter-arrival times between cases
        thiscase_arrival_time = thiscase_events.loc[thiscase_events['activity']=='arrival', 'time'].values[0]
        inter_arrival_time = thiscase_arrival_time - lastcase_arrival_time
        inter_arrival_times.append(inter_arrival_time)
        print(file = fcasedata)
        print('time between arrivals (this case minus previous case):',inter_arrival_time, 'seconds', file = fcasedata)
        lastcase_arrival_time  = thiscase_arrival_time # save for next case in the for-loop
        # compute waiting times within this case (must have begin_service event/activity)
        if thiscase_events.loc[thiscase_events['activity']=='begin_service'].shape[0] == 1:
            thiscase_begin_service = thiscase_events.loc[thiscase_events['activity']=='begin_service', 'time'].values[0]
            thiscase_join_queue = thiscase_arrival_time = thiscase_events.loc[thiscase_events['activity']=='join_queue', 'time'].values[0]
            thiscase_waiting_time = thiscase_begin_service - thiscase_join_queue
            waiting_time.append(thiscase_waiting_time)
            print('waiting time for this case (time between joining queue and beginning service):',thiscase_waiting_time, 'seconds', file = fcasedata)
        # compute service time within this case (must have end_service event/activity)
        if thiscase_events.loc[thiscase_events['activity']=='end_service'].shape[0] == 1:
            thiscase_end_service = thiscase_events.loc[thiscase_events['activity']=='end_service', 'time'].values[0]
            thiscase_service_time = thiscase_end_service - thiscase_begin_service
            service_time.append(thiscase_service_time)
            print('service time for this case (time between beginning and ending service):',thiscase_service_time, 'seconds', file = fcasedata)
        
print()     
print('Summary statistics for customer inter-arrival times:')
print('  Minimum: ',round(np.min(inter_arrival_times),2), ' seconds (' ,round(np.min(inter_arrival_times)/60,2), ' minutes)',sep='')  
print('  Mean:    ',round(np.average(inter_arrival_times),2), ' seconds (' ,round(np.average(inter_arrival_times)/60,2), ' minutes)',sep='')  
print('  Maximum: ',round(np.max(inter_arrival_times),2), ' seconds (' ,round(np.max(inter_arrival_times)/60,2), ' minutes)',sep='')      
print()
print('Summary statistics for customer wait times:')
print('  Minimum: ',round(np.min(waiting_time),2), ' seconds (' ,round(np.min(waiting_time)/60,2), ' minutes)',sep='')  
print('  Mean:    ',round(np.average(waiting_time),2), ' seconds (' ,round(np.average(waiting_time)/60,2), ' minutes)',sep='')  
print('  Maximum: ',round(np.max(waiting_time),2), ' seconds (' ,round(np.max(waiting_time)/60,2), ' minutes)',sep='')  
print()
print('Summary statistics for service times:')
print('  Minimum: ',round(np.min(service_time),2), ' seconds (' ,round(np.min(service_time)/60,2), ' minutes)',sep='')  
print('  Mean:    ',round(np.average(service_time),2), ' seconds (' ,round(np.average(service_time)/60,2), ' minutes)',sep='')  
print('  Maximum: ',round(np.max(service_time),2), ' seconds (' ,round(np.max(service_time)/60,2), ' minutes)',sep='')  

