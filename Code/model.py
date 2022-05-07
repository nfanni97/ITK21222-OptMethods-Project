from __future__ import annotations
from asyncio import transports
from typing import Dict,List


class City:
    def __init__(self, name: str, cap: int, transports: Dict[City, int], base: int = 0) -> None:
        self.name: str = name
        self.capacity: int = cap  # capacity/supply/demand
        self.current_capacity = 0
        self.base_cost: int = base  # for source cities
        self.transports: Dict[City, int] = transports  # cost of destination

    def can_transport_to(self, dest: City, amount: int) -> bool:
        return dest in self.transports and amount <= self.current_capacity and amount+dest.current_capacity <= dest.capacity
    
    def __str__(self) -> str:
        r = f'name: {self.name}, base: {self.base_cost}, {self.current_capacity}/{self.capacity}'
        for city,cost in self.transports.items():
            r += f'\n\t{city.name} -> {cost}'
        return r


class Transport:
    def __init__(self, source: City, dest: City, units: int, cost: int) -> None:
        self.source: City = source
        self.destination: City = dest
        self.units: int = units
        self.cost: int = cost  # per unit

    def get_total(self) -> int:
        return self.units*self.cost
    
    def __radd__(self,other: int) -> int:
        return self.get_total()+other


class Model:
    def __init__(self, cities: List[City]) -> None:
        self.cities: List[City] = cities
        self.transports: List[Transport] = []

    @property
    def cost(self) -> int:
        return sum(self.transport,0)

    # TODO: different method?
    def transport(self, source: City, dest: City, amount: int) -> None:
        if not source.can_transport_to(dest, amount):
            raise Exception(
                f'cannot transport {amount} units from {self.name} to {dest.name}')
        source.current_capacity -= amount
        dest.current_capacity += amount
        self.transports.append(Transport(source,dest,amount,source.transports[dest]))
