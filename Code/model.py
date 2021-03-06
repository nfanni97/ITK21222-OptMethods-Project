from __future__ import annotations
import math
from typing import Dict, List, Tuple
import logging
import random

# TODO: city: current capacity = source cap+dest cap for different treating ICO B

class City:
    def __init__(self, name: str, cap: int, transports: Dict[City, int], base: int = 0) -> None:
        self.logger = logging.getLogger('City')
        self.name: str = name
        self.capacity: int = cap  # supply for source, demand for destination
        self.current_source_capacity = 0
        self.current_dest_capacity = 0
        self.base_cost: int = base  # for source cities
        self.transports: Dict[City, int] = transports  # cost of destination

    def can_transport_to(self, dest: City, amount: int) -> bool:
        return dest in self.transports and amount+self.current_source_capacity <= self.capacity and amount+dest.current_dest_capacity <= dest.capacity

    def __str__(self) -> str:
        r = f'name: {self.name}, base: {self.base_cost}, s{self.current_source_capacity},d{self.current_dest_capacity}/{self.capacity}'
        for city, cost in self.transports.items():
            r += f'\n\t{city.name} -> {cost}'
        return r


class Transport:
    def __init__(self, source: City, dest: City, units: int, cost: int) -> None:
        self.logger = logging.getLogger('Transport')
        self.source: City = source
        self.destination: City = dest
        self.units: int = units
        self.cost: int = cost  # per unit

    def get_total(self) -> int:
        return self.units*self.cost

    def __radd__(self, other: int) -> int:
        return self.get_total()+other

    def __eq__(self, __o: object) -> bool:
        if isinstance(__o, Transport):
            return self.source == __o.source and self.destination == __o.destination
        return False

    def __str__(self) -> str:
        return f'{self.units} from {self.source.name} to {self.destination.name}'


class SubModel:
    def __init__(self, sources: List[City], dests: List[City]) -> None:
        self.logger = logging.getLogger('SubModel')
        self.sources: List[City] = sources
        self.destinations: List[City] = dests
        self.transports: List[Transport] = []

    def backwards_greedy(self) -> None:
        logger = self.logger.getChild('backwards_greedy')
        # backwards greedy:
        for d in self.destinations:
            logger.debug(f'filling {d.name}')
            # fill with Bs until full
            for current_s in self.sources:
                if d in current_s.transports:
                    # transport max possible
                    transport(current_s, d, min(d.capacity-d.current_dest_capacity, current_s.capacity-current_s.current_source_capacity),self.transports,logger)
                if d.current_dest_capacity == d.capacity:
                    break
            if d.current_dest_capacity != d.capacity:
                raise Exception(
                    f'exceeded all Bs but {d.name} is still not full')


class Model:
    def __init__(self, cities: List[City]) -> None:
        self.logger = logging.getLogger('Model')
        self.cities: List[City] = cities
        self.transports: List[Transport] = []

    @property
    def cost(self) -> int:
        return sum(self.transports, 0) + sum([c.base_cost for c in self.cities if c.current_source_capacity > 0 and c.name[0] == 'A'], 0)

    @property
    def cities_A(self) -> List[City]:
        return [c for c in self.cities if c.name[0] == 'A']

    @property
    def cities_B(self) -> List[City]:
        return [c for c in self.cities if c.name[0] == 'B']

    @property
    def cities_C(self) -> List[City]:
        return [c for c in self.cities if c.name[0] == 'C']

    def greedy_feasible(self) -> None:
        logger = self.logger.getChild('greedy_feasible')
        logger.info(f'finding new feasible solution')
        # start with B -> C
        logger.info(f'transporting from B to C')
        m2: Model = SubModel(self.cities_B, self.cities_C)
        m2.backwards_greedy()
        logger.info(f'finished with basic solution for b->c')
        for t in m2.transports:
            logger.debug(t)
        # then A -> B: set demand for B to the ones computed in previous step
        # but save them first!
        original_B_capacity: Dict[City,int] = {b: b.capacity for b in self.cities_B}
        # and reset currents
        for b in self.cities_B:
            b.capacity = b.current_source_capacity
        logger.debug(f'new capacities for Bs:')
        for b in self.cities_B:
            logger.debug(f'{b.name}: {b.capacity}')
        m1: SubModel = SubModel(self.cities_A,self.cities_B)
        m1.backwards_greedy()
        # load all created transports
        self.transports = m1.transports + m2.transports
        # reset capacities to originals
        for i in range(len(self.cities)):
            if self.cities[i].name[0] == 'B':
                self.cities[i].capacity = original_B_capacity[self.cities[i]]
        logger.debug(f'all transports:')
        for t in self.transports:
            logger.debug(f'\t{t}')
        print(f'the cost of the greedy feasible solution: {self.cost}')
        
    def simulated_annealing(self,max_iter: int,fine_tune_iters: int,starting_T: float, decrease_value: float) -> int:
        logger = self.logger.getChild('simulated_annealing')
        # initial cost
        self.greedy_feasible()
        current_z = self.cost
        logger.debug(f'initial cost: {current_z}')
        T = starting_T
        current_iter: int = 0
        while current_iter < max_iter-fine_tune_iters:
            if current_z < 0:
                logger.error(f'NEGATIVE COST!')
                raise Exception(f'negative cost! {current_z}')
            logger.debug(f'#{current_iter}')
            # get new problem
            s_1,s_2,d,moved = self.mutate_solution()
            new_z = self.cost
            logger.debug(f'new cost: {new_z}')
            if new_z < current_z:
                current_z = new_z
                logger.debug(f'new cost lower, accepting')
            else:
                p = random.random()
                logger.debug(f'new cost larger or same, p = {p}')
                q = math.exp((current_z-new_z)/T)
                logger.debug(f'q = {q}')
                if q > p:
                    logger.debug(f'q was larger than p, accepting new candidate')
                    current_z = new_z
                else:
                    logger.debug(f'q was smaller than p, going back to original solution')
                    permutate_transport(s_2,s_1,d,moved,self.transports,logger)
            T -= decrease_value
            current_iter += 1
        # fine tuning
        while current_iter < max_iter:
            s_1,s_2,d,moved = self.mutate_solution(max_movable=1)
            new_z = self.cost
            logger.debug(f'new cost: {new_z}')
            if new_z < current_z:
                current_z = new_z
                logger.debug(f'new cost lower, accepting')
            else:
                p = random.random()
                logger.debug(f'new cost larger or same, p = {p}')
                q = math.exp((current_z-new_z)/T)
                logger.debug(f'q = {q}')
                if q > p:
                    logger.debug(f'q was larger than p, accepting new candidate')
                    current_z = new_z
                else:
                    logger.debug(f'q was smaller than p, going back to original solution')
                    permutate_transport(s_2,s_1,d,moved,self.transports,logger)
            current_iter += 1
            T -= decrease_value
        print(f'finished with all iterations, current cost is {self.cost}')
        return self.cost
    
    def _get_city_by_name(self,name: str) -> City:
        for c in self.cities:
            if c.name == name:
                return c
        raise Exception(f'no city named {name}')
            
    def write_to_file(self,filename: str) -> None:
        logger = self.logger.getChild('write_to_file')
        with open(f'f{filename}_ab.csv','w') as f:
            f.write(f'A,{",".join("B"+str(i) for i in range(1,6))}\n')
            for a in range(1,9):
                f.write(f'A{a}')
                for b in range(1,6):
                    t = Transport(self._get_city_by_name(f'A{a}'),self._get_city_by_name(f'B{b}'),0,0)
                    if t in self.transports:
                        f.write(f',{self.transports[self.transports.index(t)].units}')
                    else:
                        f.write(',0')
                f.write('\n')
        with open(f'{filename}_bc.csv','w') as f:
            f.write(f'B,{",".join("C"+str(i) for i in range(1,10))}\n')
            for b in range(1,6):
                f.write(f'B{b}')
                for c in range(1,10):
                    t = Transport(self._get_city_by_name(f'B{b}'),self._get_city_by_name(f'C{c}'),0,0)
                    if t in self.transports:
                        f.write(f',{self.transports[self.transports.index(t)].units}')
                    else:
                        f.write(',0')
                f.write('\n')
        
        
    def _get_sources_destination(self,sources) -> Tuple[City,City,City]:
        # find a destination and a source randomly (d,s_1, respectively) between which there is already a transport
        s_1: City = random.choice([t.source for t in self.transports if t.source in sources])
        d: City = random.choice([t.destination for t in self.transports if t.source == s_1])
        # find another source that is not full
        s_2: City = random.choice([c for c in sources if c != s_1 and c.current_source_capacity < c.capacity])
        return s_1,s_2,d
        
    def mutate_solution(self,max_movable: int = None) -> Tuple[City,City,City,int]:
        logger = self.logger.getChild('mutate_solution')
        s_1,s_2,d = self._get_sources_destination(self.cities_A)
        # transport x units from s_2 instead of s_1
        logger.debug(f'trying to mutate {s_1.name}->{d.name} to {s_1.name}+{s_2.name}->{d.name}')
        logger.debug(f's_1 {s_1.name} current capacity {s_1.current_source_capacity}, s_2 {s_2.name} leftover {s_2.capacity-s_2.current_source_capacity}')
        # max_movable: min(how much s_1 transports to d, how much s_2 has left)
        if max_movable is None:
            max_movable: int = min(
                self.transports[self.transports.index(Transport(s_1,d,0,0))].units,
                s_2.capacity-s_2.current_source_capacity)
        logger.debug(f'max movable is {max_movable}')
        if max_movable == 1:
            to_move: int = 1
        else:
            to_move: int = random.randint(1,max_movable)
        permutate_transport(s_1,s_2,d,to_move,self.transports, logger)
        return s_1,s_2,d,to_move
        
def permutate_transport(s_1: City, s_2: City,d: City,amount: int, transports: List[Transport], parentLogger: logging.Logger) -> None:
    logger: logging.Logger = parentLogger.getChild('permutate_transport')
    logger.info(f'permutating transport between {s_1.name}/{s_2.name} -> {d.name}')
    # get original transport
    original: Transport = transports[transports.index(Transport(s_1,d,0,0))]
    logger.debug(f'found original transport: {original}')
    original.units -= amount
    original.source.current_source_capacity -= amount
    original.destination.current_dest_capacity -= amount
    logger.debug(f'after removing {amount}: {original}')
    if original.units == 0:
        logger.debug(f'amount decreased to zero, removing from list')
        transports.remove(original)
    if Transport(s_2,d,0,0) in transports:
        logger.debug(f'there was already transport: {transports[transports.index(Transport(s_2,d,0,0))]}')
    # transport through s_2 instead
    transport(s_2,d,amount,transports,logger)
    logger.debug(f'new transport: {transports[transports.index(Transport(s_2,d,0,0))]}')

            
def transport(source: City, dest: City, amount: int, previous_transports: List[Transport],parentLogger: logging.Logger) -> None:
        # allow incremental transport
        if amount > 0:
            logger = parentLogger.getChild('transport')
            logger.info(
                f'transporting {amount} units from {source.name} to {dest.name}')
            if not source.can_transport_to(dest, amount):
                raise Exception(
                    f'cannot transport {amount} units from {source.name} to {dest.name}')
            source.current_source_capacity += amount
            dest.current_dest_capacity += amount
            try:
                new_transport = Transport(
                    source, dest, amount, source.transports[dest])
                idx = previous_transports.index(new_transport)
                logger.debug(
                    f'found transport from {source.name} to {dest.name} already, with {previous_transports[idx].units} units')
                previous_transports[idx].units += amount
            except ValueError:
                logger.debug(
                    f'did not find transport from {source.name} to {dest.name}, creating new')
                previous_transports.append(
                    Transport(source, dest, amount, source.transports[dest]))            
