from fastapi import FastAPI, Body, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, TypeAdapter,BeforeValidator
from dotenv import dotenv_values
from bson import ObjectId
from typing import Annotated, List, Optional
from datetime import datetime, timedelta
from pymongo import ReturnDocument
from fastapi.middleware.cors import CORSMiddleware
import motor.motor_asyncio
from fastapi import FastAPI
import re
import requests 

config = dotenv_values(".env")
config["MONGO_URL"]
client = motor.motor_asyncio.AsyncIOMotorClient(config["MONGO_URL"])
db = client.ECSE3038_Project_Database

app = FastAPI()


format = "%Y-%m-%d %H:%M:%S %Z%z"

origins = ["http://127.0.0.1:8000",
            "https://simple-smart-hub-client.netlify.app",
            "http://192.168.102.46:8000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PyObjectId = Annotated[str, BeforeValidator(str)]


class Settings(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    user_temp: Optional[float] = None
    user_light: Optional[str] = None
    light_off: Optional[str] = None
    light_duration: Optional[str] = None


class updatedSettings(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    user_temp: Optional[float] = None
    user_light: Optional[str] = None
    light_off: Optional[str] = None


class sensors(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    temperature: Optional[float] = None
    presence: Optional[bool] = None
    datetime: Optional[str] = None


regex = re.compile(r'((?P<hours>\d+?)h)?((?P<minutes>\d+?)m)?((?P<seconds>\d+?)s)?')


def parse_time(time_str):
    parts = regex.match(time_str)
    if not parts:
        return
    parts = parts.groupdict()
    time_params = {}
    for name, param in parts.items():
        if param:
            time_params[name] = int(param)
    return timedelta(**time_params)


def convert24(time):
    # Parse the time string into a datetime object
    t = datetime.strptime(time, '%I:%M:%S %p')
    # Format the datetime object into a 24-hour time string
    return t.strftime('%H:%M:%S')


def sunset_calculation():
    URL = "https://api.sunrisesunset.io/json"
    PARAMS = {"lat": "10.42971",
              "lng": "-61.37352"}
    r = requests.get(url=URL, params=PARAMS)
    response = r.json()
    sunset_time = response["results"]["sunset"]
    sunset_24 = convert24(sunset_time)
    return sunset_24


# get request to collect environmental data from ESP
@app.get("/graph")
async def get_data(size: int = None):
    try:
        data = await db["data"].find().to_list(size)
        return TypeAdapter(List[sensors]).validate_python(data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving data: {str(e)}")


@app.put("/settings", status_code=200)
async def update_settings(settings_update: Settings = Body(...)):
    if settings_update.user_light == "sunset":
        user_light = datetime.strptime(sunset_calculation(), "%H:%M:%S")
    else:
        user_light = datetime.strptime(settings_update.user_light, "%H:%M:%S")

    duration = parse_time(settings_update.light_duration)
    settings_update.light_time_off = (user_light + duration).strftime("%H:%M:%S")
    
    all_settings = await db["settings"].find().to_list(999)
    if len(all_settings)==1:
        db["settings"].update_one({"_id":all_settings[0]["_id"]},{"$set":settings_update.model_dump(exclude = ["light_duration"])})
        updated_settings = await db["settings"].find_one({"_id": all_settings[0]["_id"]})
        return updatedSettings(**updated_settings)
    
    else:
        new_settings = await db["settings"].insert_one(settings_update.model_dump(exclude = ["light_duration"]))
        created_settings = await db["settings"].find_one({"_id": new_settings.inserted_id})
        final = (updatedSettings(**created_settings)).model_dump()
        # raise HTTPException(status_code=201)
        return JSONResponse(status_code=201, content=final)
    
@app.post("/sensors",status_code=201)
async def createSensors(sensor_data:sensors):
    entry_time = datetime.now().strftime("%H:%M:%S")
    sensor_data_ = sensor_data.model_dump()
    sensor_data_["datetime"] = entry_time
    new_data = await db["sensors"].insert_one(sensor_data.model_dump())
    created_data = await db["sensors"].find_one({"_id": new_data.inserted_id})
    return sensors(**created_data)

@app.get("/sensors", status_code=200)
async def get_device_states():
    data = await db["sensors"].find().to_list(999)
    num = len(data) - 1
    sensor = data[num]

    all_settings = await db["settings"].find().to_list(999)
    user_pref = all_settings[0]

    parts = {
        "fan": False,
        "light": False
    }

    if ((sensor["temperature"] == user_pref["user_temp"]) & (sensor["presence"] == True) ):
        parts["fan"] = True
    else:
        parts["fan"] = False
    
    if ((sensor["datetime"] == user_pref["user_light"]) & (sensor["presence"] == True) ):
        parts["light"] = True
    else:
        parts["light"] = False
    
    return parts

@app.get("/sensors", status_code=200)
async def turn_on_components():
    data = await db["data"].find().to_list(999)

    # to use last entry in database
    last = len(data) - 1
    sensor_data = data[last]

    settings = await db["settings"].find().to_list(999)
    
    user_setting = settings[0]

    # if someone is in the room, turn on?
    if (sensor_data["presence"] == True):
        # if temperature is hotter or equal to temp, turn on fan
        if (sensor_data["temperature"] >= user_setting["user_temp"]):
            fanState = True
        # else, turn it off
        else:
            fanState = False

        # if current time is equal to the slated turn on time, turn on light
        if (user_setting["user_light"] == sensor_data["datetime"]):
            lightState =  True
    
        else:
            on_check = await db["data"].find_one({"datetime": user_setting["user_light"]})
            off_check = await db["data"].find_one({"datetime": user_setting["light_time_off"]})
            
            # if current time is equal to the slated turn off time, turn off light
            if (user_setting["light_time_off"] == sensor_data["datetime"]):
                lightState =  False
            else:
                # if a previous current time matches with the setting OFF time, that means the light off time has passed and light should be off
                if(off_check != ""):
                    lightState = False
                # if off time has NOT passed, check if ON time has passed
                else:
                    # if a previous current time matches with the setting time, that means the light was on but hasn't turn off yet, therefore must be on
                    if(on_check != ""):
                        lightState = True
                    # otherwise, the turn on time hasn't come, light must be off
                    else:
                        lightState = False


        return_sensor_data = {
        "fan": fanState,
        "light": lightState
        }

    # if no one in room, everything off
    else:
        return_sensor_data = {
        "fan": False,
        "light": False
    }
    return return_sensor_data