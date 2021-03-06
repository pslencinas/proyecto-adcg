from sqlalchemy import Column, ForeignKey, Integer, String, Date
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine

Base = declarative_base()

class User(Base):
	__tablename__ = 'user'

	id = Column(Integer, primary_key=True)
	name = Column(String(250), nullable=False)
	email = Column(String(250), nullable=False)
	picture = Column(String(250))

class Bajas(Base):
    __tablename__ = 'bajas'

    id = Column(Integer, primary_key = True)
    razonSocial = Column(String(10))
    sucursal = Column(String(100))
    usuaria = Column(String(100))
    nombre = Column(String(100))
    apellido = Column(String(100))
    cuit = Column(String(20))
    fechaIngreso = Column(Date)
    fechaEgreso = Column(Date)
    fechaBaja = Column(Date)
    mejorRemu = Column(String(20))
    situacion = Column(String(50))
    suspensionDesde = Column(Date)
    suspensionHasta = Column(Date)
    comentarios = Column(String(500))
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship(User)

    @property
    def serialize(self):
       """Return object data in easily serializeable format"""
       return {
           'id'         : self.id,
           'razon_social'	: self.razon_social,
           'usuaria'	: self.usuaria,
           'nombre' : self.nombre,
           'apellido'	: self.apellido,
           'cuit' : self.cuit,
           'mejor_remu' : self.mejor_remu,
           'comentarios' : self.comentarios
       }

engine = create_engine('postgresql://adecco:adecco2009@localhost/adeccodb')

Base.metadata.create_all(engine)
