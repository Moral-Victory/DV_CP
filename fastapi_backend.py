from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

app = FastAPI(title="Lathe Predictive Maintenance API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins in development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB connection
try:
    client = MongoClient("mongodb://localhost:27017/")
    db = client["lathe_maintenance"]
    print("Connected to MongoDB successfully!")
except Exception as e:
    print(f"Failed to connect to MongoDB: {e}")


# Pydantic models
class LatheSummary(BaseModel):
    lathe_id: int
    name: str
    health_score: float
    uptime: float
    status: str


class LatheDetails(BaseModel):
    lathe_id: int
    name: str
    health_score: float
    uptime: float
    status: str
    air_temperature: float
    process_temperature: float
    rotational_speed: float
    torque: float
    tool_wear: float
    vibration: Optional[float] = None
    failure_count: int
    product_types: Dict[str, int]


# Routes
@app.get("/")
def read_root():
    return {"message": "Welcome to Lathe Predictive Maintenance API"}


@app.get("/lathes", response_model=List[LatheSummary])
def get_all_lathes():
    """Get summary information for all lathes"""
    lathes = []
    
    # Check each potential lathe collection
    for i in range(1, 5):
        collection_name = f"lathe_m{i}"
        if collection_name in db.list_collection_names():
            collection = db[collection_name]
            
            # Get the most recent data
            data = list(collection.find().sort("timestamp", -1).limit(50))
            if data:
                df = pd.DataFrame(data)
                
                # Calculate average health score and uptime
                avg_health = df["Health score"].mean()
                avg_uptime = df["Uptime"].mean() if "Uptime" in df.columns else 0
                
                # Determine status based on health score
                if avg_health >= 80:
                    status = "Operational"
                elif avg_health >= 60:
                    status = "Warning"
                else:
                    status = "Failure"
                
                lathes.append(
                    LatheSummary(
                        lathe_id=i,
                        name=f"Lathe M{i}",
                        health_score=round(avg_health, 1),
                        uptime=round(avg_uptime, 1),
                        status=status
                    )
                )
    
    return lathes


@app.get("/lathes/{lathe_id}", response_model=LatheDetails)
def get_lathe_details(lathe_id: int):
    """Get detailed information for a specific lathe"""
    collection_name = f"lathe_m{lathe_id}"
    
    if collection_name not in db.list_collection_names():
        raise HTTPException(status_code=404, detail=f"Lathe M{lathe_id} not found")
    
    collection = db[collection_name]
    data = list(collection.find().sort("timestamp", -1).limit(100))
    
    if not data:
        raise HTTPException(status_code=404, detail=f"No data found for Lathe M{lathe_id}")
    
    df = pd.DataFrame(data)
    
    # Calculate metrics
    avg_health = df["Health score"].mean()
    avg_uptime = df["Uptime"].mean() if "Uptime" in df.columns else 0
    
    # Determine status based on health score
    if avg_health >= 80:
        status = "Operational"
    elif avg_health >= 60:
        status = "Warning"
    else:
        status = "Failure"
    
    # Count product types
    product_types = df["Type"].value_counts().to_dict() if "Type" in df.columns else {}
    
    # Count failures
    failure_count = df["Failure"].sum() if "Failure" in df.columns else 0
    
    return LatheDetails(
        lathe_id=lathe_id,
        name=f"Lathe M{lathe_id}",
        health_score=round(avg_health, 1),
        uptime=round(avg_uptime, 1),
        status=status,
        air_temperature=round(df["Air temperature"].mean(), 1),
        process_temperature=round(df["Process temperature"].mean(), 1),
        rotational_speed=round(df["Rotational speed"].mean(), 1),
        torque=round(df["Torque"].mean(), 1),
        tool_wear=round(df["Tool wear"].mean(), 1),
        vibration=round(df["Vibration"].mean(), 1) if "Vibration" in df.columns else None,
        failure_count=int(failure_count),
        product_types=product_types
    )


@app.get("/lathes/{lathe_id}/sensor-data")
def get_lathe_sensor_data(lathe_id: int):
    """Get sensor data for a specific lathe"""
    collection_name = f"lathe_m{lathe_id}"
    
    if collection_name not in db.list_collection_names():
        raise HTTPException(status_code=404, detail=f"Lathe M{lathe_id} not found")
    
    collection = db[collection_name]
    data = list(collection.find().sort("timestamp", -1).limit(100))
    
    if not data:
        raise HTTPException(status_code=404, detail=f"No data found for Lathe M{lathe_id}")
    
    df = pd.DataFrame(data)
    
    # Extract sensor data
    sensor_data = {
        "air_temperature": df["Air temperature"].tolist(),
        "process_temperature": df["Process temperature"].tolist(),
        "rotational_speed": df["Rotational speed"].tolist(),
        "torque": df["Torque"].tolist(),
        "tool_wear": df["Tool wear"].tolist(),
    }
    
    if "Vibration" in df.columns:
        sensor_data["vibration"] = df["Vibration"].tolist()
    
    # Calculate min, max, avg for each sensor
    stats = {}
    for key, values in sensor_data.items():
        stats[key] = {
            "min": round(min(values), 2),
            "max": round(max(values), 2),
            "avg": round(sum(values) / len(values), 2)
        }
    
    return {
        "lathe_id": lathe_id,
        "name": f"Lathe M{lathe_id}",
        "sensor_data": sensor_data,
        "stats": stats
    }


@app.get("/lathes/{lathe_id}/product-analysis")
def get_lathe_product_analysis(lathe_id: int):
    """Get product type analysis for a specific lathe"""
    collection_name = f"lathe_m{lathe_id}"
    
    if collection_name not in db.list_collection_names():
        raise HTTPException(status_code=404, detail=f"Lathe M{lathe_id} not found")
    
    collection = db[collection_name]
    data = list(collection.find())
    
    if not data:
        raise HTTPException(status_code=404, detail=f"No data found for Lathe M{lathe_id}")
    
    df = pd.DataFrame(data)
    
    # Product type distribution
    product_types = df["Type"].value_counts().to_dict() if "Type" in df.columns else {}
    
    # Product quality by type (failure rate per type)
    product_quality = {}
    if "Type" in df.columns and "Failure" in df.columns:
        for product_type in df["Type"].unique():
            type_df = df[df["Type"] == product_type]
            failure_rate = type_df["Failure"].mean() * 100
            product_quality[product_type] = {
                "count": len(type_df),
                "failure_rate": round(failure_rate, 2),
                "avg_health_score": round(type_df["Health score"].mean(), 2) if "Health score" in df.columns else 0
            }
    
    # Average parameters by product type
    params_by_type = {}
    if "Type" in df.columns:
        for product_type in df["Type"].unique():
            type_df = df[df["Type"] == product_type]
            params_by_type[product_type] = {
                "air_temperature": round(type_df["Air temperature"].mean(), 2),
                "process_temperature": round(type_df["Process temperature"].mean(), 2),
                "rotational_speed": round(type_df["Rotational speed"].mean(), 2),
                "torque": round(type_df["Torque"].mean(), 2),
                "tool_wear": round(type_df["Tool wear"].mean(), 2)
            }
    
    return {
        "lathe_id": lathe_id,
        "name": f"Lathe M{lathe_id}",
        "product_types": product_types,
        "product_quality": product_quality,
        "params_by_type": params_by_type
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)