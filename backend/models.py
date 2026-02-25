"""SQLAlchemy models for RigLab-AI drilling monitoring."""

from sqlalchemy import Column, Integer, DateTime, Float, String

from backend.database import Base


class CalculatedData(Base):
    """Stores calculated drilling data with situation classification."""

    __tablename__ = "calculated_data"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False)
    mw_ppg = Column(Float, nullable=False)  # Mud Weight (ppg)
    gate_angle = Column(Float, nullable=False)  # Sensor value for kick detection
    viscosity = Column(Float, nullable=False)  # Apparent Viscosity
    situation = Column(String(20), nullable=False)  # 'Normal', 'Kick', or 'Loss'
