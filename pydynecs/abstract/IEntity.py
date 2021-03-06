"""pydynecs/abstract/IEntity.py
@OffbyOne Studios 2014
Abstract class used as a base for entity like types, for coerceing.
"""
import abc

class IEntity(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def entity_id(self):
        """Returns the entity id."""
        pass
    
    def __hash__(self):
        return hash(self.entity_id())
    
    def __eq__(self, other):
        return self.entity_id() == other
    
    def __repr__(self):
        return "<IEntity: {}>".format(self.entity_id())
