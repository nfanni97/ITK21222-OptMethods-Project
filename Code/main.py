from model import Model, City
from typing import List, Dict
import logging

logging.basicConfig(level=logging.DEBUG,filename='log.log',filemode='w')

def get_city_object(name: str, prev_cities: List[City]) -> City:
    for c in prev_cities:
        if c.name == name:
            return c

def get_cities_with_prefix(prev_cities: List[City], prefix: str, caps_file: str, costs_file: str) -> List[City]:
    with open(caps_file) as caps:
        next(caps)
        cities: List[City] = []
        for caps_line in caps:
            caps_l = caps_line.split(',')
            # support unordered files
            if caps_l[0][:len(prefix)] != prefix:
                continue
            transports: Dict[City, int] = {}
            with open(costs_file) as costs:
                next(costs)
                for cost_line in costs:
                    cost_l = cost_line.split(',')
                    if cost_l[0] != caps_l[0]:
                        continue
                    transports[get_city_object(cost_l[1], prev_cities)] = int(cost_l[2])
            cities.append(City(caps_l[0], int(caps_l[1]), transports))
    return cities


def get_model(caps_file: str, costs_file: str) -> Model:
    # highly inefficient but oh well
    cities = get_cities_with_prefix([], 'C', caps_file, costs_file)
    cities += get_cities_with_prefix(cities, 'B', caps_file, costs_file)
    cities += get_cities_with_prefix(cities, 'A', caps_file, costs_file)
    for c in cities:
        if c.name[0] == 'A':
            c.base_cost = 2000
    return Model(cities)


if __name__ == '__main__':
    costs = []
    iters = 15000 # including fine tuning iterations
    start_T = 10000
    decrease_T = .6
    fine_tune_iters = 100
    if fine_tune_iters > iters:
        raise Exception(f'the number of fine tuning iterations ({fine_tune_iters}) should not be more than the number of iterations ({iters})')
    if decrease_T*iters > start_T:
        raise Exception(f'the value of T ({start_T}) should be at least as large as the decrease value ({decrease_T}) times iterations ({iters})')
    model: Model = get_model('problem_caps.csv', 'problem_costs.csv')
    model.simulated_annealing(iters,fine_tune_iters,start_T,decrease_T)
    model.write_to_file(f'{i+1}_sol')
