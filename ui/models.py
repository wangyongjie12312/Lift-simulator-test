from __future__ import annotations

from typing import List, Literal

from pydantic import BaseModel, Field, field_validator


class LiftPointIn(BaseModel):
    enabled: bool = True
    depth_m: float = 0.0
    stroke_m: float = 0.0
    mode: Literal["SZ", "SS"] = "SZ"


class ClientInputs(BaseModel):
    air_weight_kg: float = Field(255_000.0, gt=0)
    wet_weight_kg: float = Field(202_800.0, gt=0)
    payload_height_m: float = Field(7.0, ge=0)
    rigging_height_m: float = Field(36.0, ge=0)
    start_depth_m: float = -50.0
    final_depth_m: float = 1380.0
    lifting_sequence: List[LiftPointIn] = Field(default_factory=list)
    sea_temp_profile: Literal["Safelink formula", "Constant"] = "Safelink formula"
    air_temp_c: float = 30.0
    surface_temp_c: float = 25.0

    @field_validator("final_depth_m")
    @classmethod
    def deeper_than_start(cls, value, info):
        if value <= info.data.get("start_depth_m", 0.0):
            raise ValueError("final_depth_m must be below start_depth_m")
        return value


class SafelinkInputs(BaseModel):
    p_sz_barg: float = Field(84.2, ge=0)
    p_ss_barg: float = Field(83.1, ge=0)
    p_hp_barg: float = Field(300.0, ge=0)
    p_lp_barg: float = Field(0.0, ge=0)
    priorities: List[str] = Field(default_factory=list)
    orientation: Literal["Rod down", "Rod up"] = "Rod down"
    hysteresis_bar: float = Field(0.0, ge=0)


class SimRequest(BaseModel):
    unit_name: str
    client_inputs: ClientInputs = Field(default_factory=ClientInputs)
    safelink_inputs: SafelinkInputs = Field(default_factory=SafelinkInputs)
    depth_steps: int = Field(241, ge=2, le=5000)