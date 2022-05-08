from __future__ import annotations
import math
from typing import Dict, List, Tuple
import logging
import random


class City:
    def __init__(self, name: str, cap: int, transports: Dict[City, int], base: int = 0) -> None:
        self.logger = logging.getLogger('City')
        self.name: str = name
        self.capacity: int = cap  # supply for source, demand for destination
        self.current_capacity = 0
        self.base_cost: int = base  # for source cities
        self.transports: Dict[City, int] = transports  # cost of destination

    def can_transport_to(self, dest: City, amount: int) -> bool:
        return dest in self.transports and amount+self.current_capacity <= self.capacity and amount+dest.current_capacity <= dest.capacity

    def __str__(self) -> str:
        r = f'name: {self.name}, base: {self.base_cost}, {self.current_capacity}/{self.capacity}'
        for city, cost in self.transports.items():
            r += f'\n\t{city.name} -> {cost}'
        return r

    @property
    def is_full(self) -> bool:
        return self.capacity == self.current_capacity

    @property
    def leftover(self) -> int:
        return self.capacity-self.current_capacity


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
                    transport(current_s, d, min(d.leftover, current_s.leftover),self.transports,logger)
                if d.is_full:
                    break
            if not d.is_full:
                raise Exception(
                    f'exceeded all Bs but {d.name} is still not full')


class Model:
    def __init__(self, cities: List[City]) -> None:
        self.logger = logging.getLogger('Model')
        self.cities: List[City] = cities
        self.transports: List[Transport] = []

    @property
    def cost(self) -> int:
        return sum(self.transports, 0) + sum([c.base_cost for c in self.cities if c.current_capacity > 0], 0)

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
            b.capacity = b.current_capacity
            b.current_capacity = 0
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
        
    def simulated_annealing(self,max_iter: int,starting_T: float, decrease_value: float) -> None:
        logger = self.logger.getChild('simulated_annealing')
        # initial cost
        self.greedy_feasible()
        current_z = self.cost
        logger.debug(f'initial cost: {current_z}')
        T = starting_T
        current_iter: int = 0
        while current_iter < max_iter:
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
        print(f'finished with all iterations, current cost is {self.cost}')
            
            
        
        
    def _get_sources_destination(self,sources) -> Tuple[City,City,City]:
        # find a destination and a source randomly (d,s_1, respectively) between which there is already a transport
        s_1: City = random.choice(sources)
        d: City = random.choice([t.destination for t in self.transports if t.source == s_1])
        # find another source that is not full
        s_2: City = random.choice([c for c in sources if c != s_1])
        return s_1,s_2,d
        
    def mutate_solution(self) -> Tuple[City,City,City,int]:
        logger = self.logger.getChild('mutate_solution')
        # choose which layer will be modified
        isAB: bool = random.choice([True,False])
        if isAB:
            s_1,s_2,d = self._get_sources_destination(self.cities_A)
        else:
            s_1,s_2,d = self._get_sources_destination(self.cities_B)
        # transport x units from s_2 instead of s_1
        logger.debug(f'trying to mutate {s_1.name}->{d.name} to {s_1.name}+{s_2.name}->{d.name}')
        logger.debug(f's_1 {s_1.name} capacity {s_1.capacity}, s_2 {s_2.name} leftover {s_2.leftover}')
        max_movable: int = min(s_1.capacity, s_2.leftover)
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
    # transport through s_2 instead
    transport(s_2,d,amount,transports,logger)

            
def transport(source: City, dest: City, amount: int, previous_transports: List[Transport],parentLogger: logging.Logger) -> None:
        # allow incremental transport
        if amount > 0:
            logger = parentLogger.getChild('transport')
            logger.info(
                f'transporting {amount} units from {source.name} to {dest.name}')
            if not source.can_transport_to(dest, amount):
                raise Exception(
                    f'cannot transport {amount} units from {source.name} to {dest.name}')
            source.current_capacity += amount
            dest.current_capacity += amount
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
