import os
import sys
import argparse
from typing import Any, Dict, List, Optional
import requests
from mcp.server.fastmcp import FastMCP

def get_api_key() -> str:
    """Get the Amap Maps API key from environment variables"""
    api_key = os.getenv("AMAP_MAPS_API_KEY")
    if not api_key:
        raise ValueError("AMAP_MAPS_API_KEY environment variable is required")
    return api_key

AMAP_MAPS_API_KEY = get_api_key()

mcp = FastMCP("amap-maps")

@mcp.tool()
def maps_regeocode(location: str) -> Dict[str, Any]:
    """Convert Amap coordinates to administrative address information (reverse geocoding). Input must be LONGITUDE,LATITUDE format (e.g., '116.397428,39.90923')"""
    try:
        response = requests.get(
            "https://restapi.amap.com/v3/geocode/regeo",
            params={
                "key": AMAP_MAPS_API_KEY,
                "location": location
            }
        )
        response.raise_for_status()
        data = response.json()
        
        if data["status"] != "1":
            return {"error": f"RGeocoding failed: {data.get('info') or data.get('infocode')}"}
            
        return {
            "province": data["regeocode"]["addressComponent"]["province"],
            "city": data["regeocode"]["addressComponent"]["city"],
            "district": data["regeocode"]["addressComponent"]["district"]
        }
    except requests.exceptions.RequestException as e:
        return {"error": f"Request failed: {str(e)}"}

@mcp.tool()
def maps_geo(address: str, city: Optional[str] = None) -> Dict[str, Any]:
    """Convert detailed structured address to coordinates (geocoding). Supports landmarks, scenic spots, and building names. Returns coordinates in LONGITUDE,LATITUDE format"""
    try:
        params = {
            "key": AMAP_MAPS_API_KEY,
            "address": address
        }
        if city:
            params["city"] = city
            
        response = requests.get(
            "https://restapi.amap.com/v3/geocode/geo",
            params=params
        )
        response.raise_for_status()
        data = response.json()
        
        if data["status"] != "1":
            return {"error": f"Geocoding failed: {data.get('info') or data.get('infocode')}"}
            
        geocodes = data.get("geocodes", [])
        results = []
        for geo in geocodes:
            results.append({
                "country": geo.get("country"),
                "province": geo.get("province"),
                "city": geo.get("city"),
                "citycode": geo.get("citycode"),
                "district": geo.get("district"),
                "street": geo.get("street"),
                "number": geo.get("number"),
                "adcode": geo.get("adcode"),
                "location": geo.get("location"),
                "level": geo.get("level")
            })
        return {"return": results}
    except requests.exceptions.RequestException as e:
        return {"error": f"Request failed: {str(e)}"}

@mcp.tool()
def maps_ip_location(ip: str) -> Dict[str, Any]:
    """Locate the geographic position of an IP address"""
    try:
        response = requests.get(
            "https://restapi.amap.com/v3/ip",
            params={
                "key": AMAP_MAPS_API_KEY,
                "ip": ip
            }
        )
        response.raise_for_status()
        data = response.json()
        
        if data["status"] != "1":
            return {"error": f"IP Location failed: {data.get('info') or data.get('infocode')}"}
            
        return {
            "province": data.get("province"),
            "city": data.get("city"),
            "adcode": data.get("adcode"),
            "rectangle": data.get("rectangle")
        }
    except requests.exceptions.RequestException as e:
        return {"error": f"Request failed: {str(e)}"}

@mcp.tool()
def maps_weather(city: str) -> Dict[str, Any]:
    """Query weather information for a specified city by city name or adcode"""
    try:
        response = requests.get(
            "https://restapi.amap.com/v3/weather/weatherInfo",
            params={
                "key": AMAP_MAPS_API_KEY,
                "city": city,
                "extensions": "all"
            }
        )
        response.raise_for_status()
        data = response.json()
        
        if data["status"] != "1":
            return {"error": f"Get weather failed: {data.get('info') or data.get('infocode')}"}
            
        forecasts = data.get("forecasts", [])
        if not forecasts:
            return {"error": "No forecast data available"}
            
        return {
            "city": forecasts[0]["city"],
            "forecasts": forecasts[0]["casts"]
        }
    except requests.exceptions.RequestException as e:
        return {"error": f"Request failed: {str(e)}"}

@mcp.tool()
def maps_bicycling_by_address(origin_address: str, destination_address: str, origin_city: Optional[str] = None, destination_city: Optional[str] = None) -> Dict[str, Any]:
    """Plans a bicycle route between two locations using addresses. Unless you have a specific reason to use coordinates, it's recommended to use this tool.
    
    Args:
        origin_address (str): Starting point address (e.g. "6 Futong East Street, Chaoyang District, Beijing")
        destination_address (str): Ending point address (e.g. "10 Shangdi 10th Street, Haidian District, Beijing")
        origin_city (Optional[str]): Optional city name for the origin address to improve geocoding accuracy
        destination_city (Optional[str]): Optional city name for the destination address to improve geocoding accuracy
        
    Returns:
        Dict[str, Any]: Route information including distance, duration, and turn-by-turn instructions.
        Considers bridges, one-way streets, and road closures. Supports routes up to 500km.
    """
    try:
        # Convert origin address to coordinates
        origin_result = maps_geo(origin_address, origin_city)
        if "error" in origin_result:
            return {"error": f"Failed to geocode origin address: {origin_result['error']}"}
        
        if not origin_result.get("return") or not origin_result["return"]:
            return {"error": "No geocoding results found for origin address"}
        
        origin_location = origin_result["return"][0].get("location")
        if not origin_location:
            return {"error": "Could not extract coordinates from origin geocoding result"}
        
        # Convert destination address to coordinates
        destination_result = maps_geo(destination_address, destination_city)
        if "error" in destination_result:
            return {"error": f"Failed to geocode destination address: {destination_result['error']}"}
        
        if not destination_result.get("return") or not destination_result["return"]:
            return {"error": "No geocoding results found for destination address"}
        
        destination_location = destination_result["return"][0].get("location")
        if not destination_location:
            return {"error": "Could not extract coordinates from destination geocoding result"}
        
        # Use the coordinates to plan the bicycle route
        route_result = maps_bicycling_by_coordinates(origin_location, destination_location)
        
        # Add address information to the result
        if "error" not in route_result:
            route_result["addresses"] = {
                "origin": {
                    "address": origin_address,
                    "coordinates": origin_location
                },
                "destination": {
                    "address": destination_address,
                    "coordinates": destination_location
                }
            }
        
        return route_result
    except Exception as e:
        return {"error": f"Route planning failed: {str(e)}"}
    
@mcp.tool()
def maps_bicycling_by_coordinates(origin_coordinates: str, destination_coordinates: str) -> Dict[str, Any]:
    """Plans a bicycle route between two coordinates.
    
    Args:
        origin_coordinates (str): Starting point coordinates in the format "longitude,latitude" (e.g. "116.434307,39.90909")
        destination_coordinates (str): Ending point coordinates in the format "longitude,latitude" (e.g. "116.434307,39.90909")
        
    Returns:
        Dict[str, Any]: Route information including distance, duration, and turn-by-turn instructions.
        Considers bridges, one-way streets, and road closures. Supports routes up to 500km.
    """
    try:
        response = requests.get(
            "https://restapi.amap.com/v4/direction/bicycling",
            params={
                "key": AMAP_MAPS_API_KEY,
                "origin": origin_coordinates,
                "destination": destination_coordinates
            }
        )
        response.raise_for_status()
        data = response.json()
        
        if data.get("errcode") != 0:
            return {"error": f"Direction bicycling failed: {data.get('info') or data.get('infocode')}"}
            
        paths = []
        for path in data["data"]["paths"]:
            steps = []
            for step in path["steps"]:
                steps.append({
                    "instruction": step.get("instruction"),
                    "road": step.get("road"),
                    "distance": step.get("distance"),
                    "orientation": step.get("orientation"),
                    "duration": step.get("duration")
                })
            paths.append({
                "distance": path.get("distance"),
                "duration": path.get("duration"),
                "steps": steps
            })
            
        return {
            "data": {
                "origin": data["data"]["origin"],
                "destination": data["data"]["destination"],
                "paths": paths
            }
        }
    except requests.exceptions.RequestException as e:
        return {"error": f"Request failed: {str(e)}"}

@mcp.tool()
def maps_direction_walking_by_address(origin_address: str, destination_address: str, origin_city: Optional[str] = None, destination_city: Optional[str] = None) -> Dict[str, Any]:
    """Plans a walking route between two locations using addresses. Unless you have a specific reason to use coordinates, it's recommended to use this tool.
    
    Args:
        origin_address (str): Starting point address (e.g. "6 Futong East Street, Chaoyang District, Beijing")
        destination_address (str): Ending point address (e.g. "10 Shangdi 10th Street, Haidian District, Beijing")
        origin_city (Optional[str]): Optional city name for the origin address to improve geocoding accuracy
        destination_city (Optional[str]): Optional city name for the destination address to improve geocoding accuracy
        
    Returns:
        Dict[str, Any]: Route information including distance, duration, and turn-by-turn instructions.
        Supports routes up to 100km.
    """
    try:
        # Convert origin address to coordinates
        origin_result = maps_geo(origin_address, origin_city)
        if "error" in origin_result:
            return {"error": f"Failed to geocode origin address: {origin_result['error']}"}
        
        if not origin_result.get("return") or not origin_result["return"]:
            return {"error": "No geocoding results found for origin address"}
        
        origin_location = origin_result["return"][0].get("location")
        if not origin_location:
            return {"error": "Could not extract coordinates from origin geocoding result"}
        
        # Convert destination address to coordinates
        destination_result = maps_geo(destination_address, destination_city)
        if "error" in destination_result:
            return {"error": f"Failed to geocode destination address: {destination_result['error']}"}
        
        if not destination_result.get("return") or not destination_result["return"]:
            return {"error": "No geocoding results found for destination address"}
        
        destination_location = destination_result["return"][0].get("location")
        if not destination_location:
            return {"error": "Could not extract coordinates from destination geocoding result"}
        
        # Use the coordinates to plan the walking route
        route_result = maps_direction_walking_by_coordinates(origin_location, destination_location)
        
        # Add address information to the result
        if "error" not in route_result:
            route_result["addresses"] = {
                "origin": {
                    "address": origin_address,
                    "coordinates": origin_location
                },
                "destination": {
                    "address": destination_address,
                    "coordinates": destination_location
                }
            }
        
        return route_result
    except Exception as e:
        return {"error": f"Route planning failed: {str(e)}"}

@mcp.tool()
def maps_direction_walking_by_coordinates(origin: str, destination: str) -> Dict[str, Any]:
    """Plan walking routes within 100km between TWO COORDINATES (NOT addresses). Coordinates must be in LONGITUDE,LATITUDE format.
    
    Args:
        origin (str): Origin coordinates in LONGITUDE,LATITUDE format (e.g., "116.434307,39.90909"). NOT latitude,longitude!
        destination (str): Destination coordinates in LONGITUDE,LATITUDE format (e.g., "116.434307,39.90909"). NOT latitude,longitude!
        
    Returns:
        Dict[str, Any]: Route information including distance, duration, and turn-by-turn instructions
    """
    try:
        response = requests.get(
            "https://restapi.amap.com/v3/direction/walking",
            params={
                "key": AMAP_MAPS_API_KEY,
                "origin": origin,
                "destination": destination
            }
        )
        response.raise_for_status()
        data = response.json()
        
        if data["status"] != "1":
            return {"error": f"Direction Walking failed: {data.get('info') or data.get('infocode')}"}
            
        paths = []
        for path in data["route"]["paths"]:
            steps = []
            for step in path["steps"]:
                steps.append({
                    "instruction": step.get("instruction"),
                    "road": step.get("road"),
                    "distance": step.get("distance"),
                    "orientation": step.get("orientation"),
                    "duration": step.get("duration")
                })
            paths.append({
                "distance": path.get("distance"),
                "duration": path.get("duration"),
                "steps": steps
            })
            
        return {
            "route": {
                "origin": data["route"]["origin"],
                "destination": data["route"]["destination"],
                "paths": paths
            }
        }
    except requests.exceptions.RequestException as e:
        return {"error": f"Request failed: {str(e)}"}

@mcp.tool()
def maps_direction_driving_by_address(origin_address: str, destination_address: str, origin_city: Optional[str] = None, destination_city: Optional[str] = None) -> Dict[str, Any]:
    """Plans a driving route between two locations using addresses. Unless you have a specific reason to use coordinates, it's recommended to use this tool.
    
    Args:
        origin_address (str): Starting point address (e.g. "6 Futong East Street, Chaoyang District, Beijing")
        destination_address (str): Ending point address (e.g. "10 Shangdi 10th Street, Haidian District, Beijing")
        origin_city (Optional[str]): Optional city name for the origin address to improve geocoding accuracy
        destination_city (Optional[str]): Optional city name for the destination address to improve geocoding accuracy
        
    Returns:
        Dict[str, Any]: Route information including distance, duration, and turn-by-turn instructions.
        Considers traffic conditions and road restrictions.
    """
    try:
        # Convert origin address to coordinates
        origin_result = maps_geo(origin_address, origin_city)
        if "error" in origin_result:
            return {"error": f"Failed to geocode origin address: {origin_result['error']}"}
        
        if not origin_result.get("return") or not origin_result["return"]:
            return {"error": "No geocoding results found for origin address"}
        
        origin_location = origin_result["return"][0].get("location")
        if not origin_location:
            return {"error": "Could not extract coordinates from origin geocoding result"}
        
        # Convert destination address to coordinates
        destination_result = maps_geo(destination_address, destination_city)
        if "error" in destination_result:
            return {"error": f"Failed to geocode destination address: {destination_result['error']}"}
        
        if not destination_result.get("return") or not destination_result["return"]:
            return {"error": "No geocoding results found for destination address"}
        
        destination_location = destination_result["return"][0].get("location")
        if not destination_location:
            return {"error": "Could not extract coordinates from destination geocoding result"}
        
        # Use the coordinates to plan the driving route
        route_result = maps_direction_driving_by_coordinates(origin_location, destination_location)
        
        # Add address information to the result
        if "error" not in route_result:
            route_result["addresses"] = {
                "origin": {
                    "address": origin_address,
                    "coordinates": origin_location
                },
                "destination": {
                    "address": destination_address,
                    "coordinates": destination_location
                }
            }
        
        return route_result
    except Exception as e:
        return {"error": f"Route planning failed: {str(e)}"}

@mcp.tool()
def maps_direction_driving_by_coordinates(origin: str, destination: str) -> Dict[str, Any]:
    """Plan driving routes between TWO COORDINATES (NOT addresses). Coordinates must be in LONGITUDE,LATITUDE format.
    
    Args:
        origin (str): Origin coordinates in LONGITUDE,LATITUDE format (e.g., "116.434307,39.90909"). NOT latitude,longitude!
        destination (str): Destination coordinates in LONGITUDE,LATITUDE format (e.g., "116.434307,39.90909"). NOT latitude,longitude!
        
    Returns:
        Dict[str, Any]: Route information including distance, duration, and turn-by-turn instructions
    """
    try:
        response = requests.get(
            "https://restapi.amap.com/v3/direction/driving",
            params={
                "key": AMAP_MAPS_API_KEY,
                "origin": origin,
                "destination": destination
            }
        )
        response.raise_for_status()
        data = response.json()
        
        if data["status"] != "1":
            return {"error": f"Direction Driving failed: {data.get('info') or data.get('infocode')}"}
            
        paths = []
        for path in data["route"]["paths"]:
            steps = []
            for step in path["steps"]:
                steps.append({
                    "instruction": step.get("instruction"),
                    "road": step.get("road"),
                    "distance": step.get("distance"),
                    "orientation": step.get("orientation"),
                    "duration": step.get("duration")
                })
            paths.append({
                "path": path.get("path"),
                "distance": path.get("distance"),
                "duration": path.get("duration"),
                "steps": steps
            })
            
        return {
            "route": {
                "origin": data["route"]["origin"],
                "destination": data["route"]["destination"],
                "paths": paths
            }
        }
    except requests.exceptions.RequestException as e:
        return {"error": f"Request failed: {str(e)}"}

@mcp.tool()
def maps_direction_transit_integrated_by_address(origin_address: str, destination_address: str, origin_city: str, destination_city: str) -> Dict[str, Any]:
    """Plans a public transit route between two locations using addresses. Unless you have a specific reason to use coordinates, it's recommended to use this tool.
    
    Args:
        origin_address (str): Starting point address (e.g. "6 Futong East Street, Chaoyang District, Beijing")
        destination_address (str): Ending point address (e.g. "10 Shangdi 10th Street, Haidian District, Beijing")
        origin_city (str): City name for the origin address (required for cross-city transit)
        destination_city (str): City name for the destination address (required for cross-city transit)
        
    Returns:
        Dict[str, Any]: Route information including distance, duration, and detailed transit instructions.
        Considers various public transit options including buses, subways, and trains.
    """
    try:
        # Convert origin address to coordinates
        origin_result = maps_geo(origin_address, origin_city)
        if "error" in origin_result:
            return {"error": f"Failed to geocode origin address: {origin_result['error']}"}
        
        if not origin_result.get("return") or not origin_result["return"]:
            return {"error": "No geocoding results found for origin address"}
        
        origin_location = origin_result["return"][0].get("location")
        if not origin_location:
            return {"error": "Could not extract coordinates from origin geocoding result"}
        
        # Convert destination address to coordinates
        destination_result = maps_geo(destination_address, destination_city)
        if "error" in destination_result:
            return {"error": f"Failed to geocode destination address: {destination_result['error']}"}
        
        if not destination_result.get("return") or not destination_result["return"]:
            return {"error": "No geocoding results found for destination address"}
        
        destination_location = destination_result["return"][0].get("location")
        if not destination_location:
            return {"error": "Could not extract coordinates from destination geocoding result"}
        
        # Use the coordinates to plan the transit route
        route_result = maps_direction_transit_integrated_by_coordinates(origin_location, destination_location, origin_city, destination_city)
        
        # Add address information to the result
        if "error" not in route_result:
            route_result["addresses"] = {
                "origin": {
                    "address": origin_address,
                    "coordinates": origin_location
                },
                "destination": {
                    "address": destination_address,
                    "coordinates": destination_location
                }
            }
        
        return route_result
    except Exception as e:
        return {"error": f"Route planning failed: {str(e)}"}

@mcp.tool()
def maps_direction_transit_integrated_by_coordinates(origin: str, destination: str, city: str, cityd: str) -> Dict[str, Any]:
    """Plan public transit routes between TWO COORDINATES (NOT addresses). Coordinates must be in LONGITUDE,LATITUDE format. For inter-city routes, origin and destination cities must be specified.
    
    Args:
        origin (str): Origin coordinates in LONGITUDE,LATITUDE format (e.g., "116.434307,39.90909"). NOT latitude,longitude!
        destination (str): Destination coordinates in LONGITUDE,LATITUDE format (e.g., "116.434307,39.90909"). NOT latitude,longitude!
        city (str): Origin city name (required for cross-city transit)
        cityd (str): Destination city name (required for cross-city transit)
        
    Returns:
        Dict[str, Any]: Route information including distance, duration, and detailed transit instructions
    """
    try:
        response = requests.get(
            "https://restapi.amap.com/v3/direction/transit/integrated",
            params={
                "key": AMAP_MAPS_API_KEY,
                "origin": origin,
                "destination": destination,
                "city": city,
                "cityd": cityd
            }
        )
        response.raise_for_status()
        data = response.json()
        
        if data["status"] != "1":
            return {"error": f"Direction Transit Integrated failed: {data.get('info') or data.get('infocode')}"}
        
        # 🔧 修复：兼容处理不同的API返回格式
        route_data = data.get("route")
        
        # 安全地获取路线信息
        if isinstance(route_data, list):
            # 如果API返回列表格式
            if not route_data:
                return {"error": "No route data available"}
            
            # 取第一个路线方案
            first_route = route_data[0]
            if not isinstance(first_route, dict):
                return {"error": f"Invalid route data format: expected dict, got {type(first_route)}"}
            
            route_info = first_route
            
        elif isinstance(route_data, dict):
            # 如果API返回字典格式
            route_info = route_data
            
        else:
            return {"error": f"Unexpected route data type: {type(route_data)}"}
        
        # 安全地处理transits数据
        transits = []
        transits_data = route_info.get("transits")
        
        if transits_data and isinstance(transits_data, list):
            for transit in transits_data:
                if not isinstance(transit, dict):
                    continue
                    
                segments = []
                segments_data = transit.get("segments")
                
                if segments_data and isinstance(segments_data, list):
                    for segment in segments_data:
                        if not isinstance(segment, dict):
                            continue
                            
                        # 安全处理walking步骤
                        walking_steps = []
                        walking_data = segment.get("walking", {})
                        if isinstance(walking_data, dict):
                            steps_data = walking_data.get("steps", [])
                            if isinstance(steps_data, list):
                                for step in steps_data:
                                    if isinstance(step, dict):
                                        walking_steps.append({
                                            "instruction": step.get("instruction", ""),
                                            "road": step.get("road", ""),
                                            "distance": step.get("distance", "0"),
                                            "action": step.get("action", ""),
                                            "assistant_action": step.get("assistant_action", "")
                                        })
                        
                        # 安全处理buslines
                        buslines = []
                        bus_data = segment.get("bus", {})
                        if isinstance(bus_data, dict):
                            buslines_data = bus_data.get("buslines", [])
                            if isinstance(buslines_data, list):
                                for busline in buslines_data:
                                    if isinstance(busline, dict):
                                        # 安全处理via_stops
                                        via_stops = []
                                        via_stops_data = busline.get("via_stops", [])
                                        if isinstance(via_stops_data, list):
                                            for stop in via_stops_data:
                                                if isinstance(stop, dict):
                                                    via_stops.append({"name": stop.get("name", "")})
                                        
                                        # 安全获取站点信息
                                        departure_stop = busline.get("departure_stop", {})
                                        arrival_stop = busline.get("arrival_stop", {})
                                        
                                        buslines.append({
                                            "name": busline.get("name", ""),
                                            "departure_stop": {
                                                "name": departure_stop.get("name", "") if isinstance(departure_stop, dict) else ""
                                            },
                                            "arrival_stop": {
                                                "name": arrival_stop.get("name", "") if isinstance(arrival_stop, dict) else ""
                                            },
                                            "distance": busline.get("distance", "0"),
                                            "duration": busline.get("duration", "0"),
                                            "via_stops": via_stops
                                        })
                        
                        # 安全获取其他段信息
                        entrance_data = segment.get("entrance", {})
                        exit_data = segment.get("exit", {})
                        railway_data = segment.get("railway", {})
                        
                        segments.append({
                            "walking": {
                                "origin": walking_data.get("origin", "") if isinstance(walking_data, dict) else "",
                                "destination": walking_data.get("destination", "") if isinstance(walking_data, dict) else "",
                                "distance": walking_data.get("distance", "0") if isinstance(walking_data, dict) else "0",
                                "duration": walking_data.get("duration", "0") if isinstance(walking_data, dict) else "0",
                                "steps": walking_steps
                            },
                            "bus": {"buslines": buslines},
                            "entrance": {
                                "name": entrance_data.get("name", "") if isinstance(entrance_data, dict) else ""
                            },
                            "exit": {
                                "name": exit_data.get("name", "") if isinstance(exit_data, dict) else ""
                            },
                            "railway": {
                                "name": railway_data.get("name", "") if isinstance(railway_data, dict) else "",
                                "trip": railway_data.get("trip", "") if isinstance(railway_data, dict) else ""
                            }
                        })
                
                transits.append({
                    "duration": transit.get("duration", "0"),
                    "walking_distance": transit.get("walking_distance", "0"),
                    "segments": segments
                })
        
        return {
            "route": {
                "origin": route_info.get("origin", origin),
                "destination": route_info.get("destination", destination),
                "distance": route_info.get("distance", "0"),
                "transits": transits
            }
        }
        
    except requests.exceptions.RequestException as e:
        return {"error": f"Request failed: {str(e)}"}
    except KeyError as e:
        return {"error": f"Missing required field in API response: {str(e)}"}
    except TypeError as e:
        return {"error": f"Data type error in API response: {str(e)}"}
    except Exception as e:
        return {"error": f"Route planning failed: {str(e)}"}

@mcp.tool()
def maps_distance(origins: str, destination: str, type: str = "1") -> Dict[str, Any]:
    """Measure distance between TWO COORDINATES (NOT addresses). Coordinates must be in LONGITUDE,LATITUDE format. Supports driving, walking, and straight-line distance measurement. Type: 1=driving, 0=straight-line, 3=walking"""
    try:
        response = requests.get(
            "https://restapi.amap.com/v3/distance",
            params={
                "key": AMAP_MAPS_API_KEY,
                "origins": origins,
                "destination": destination,
                "type": type
            }
        )
        response.raise_for_status()
        data = response.json()
        
        if data["status"] != "1":
            return {"error": f"Direction Distance failed: {data.get('info') or data.get('infocode')}"}
            
        results = []
        for result in data["results"]:
            results.append({
                "origin_id": result.get("origin_id"),
                "dest_id": result.get("dest_id"),
                "distance": result.get("distance"),
                "duration": result.get("duration")
            })
            
        return {"results": results}
    except requests.exceptions.RequestException as e:
        return {"error": f"Request failed: {str(e)}"}

@mcp.tool()
def maps_text_search(keywords: str, city: str = "", citylimit: str = "false") -> Dict[str, Any]:
    """Search for Points of Interest (POI) by keywords. Returns relevant location information"""
    try:
        response = requests.get(
            "https://restapi.amap.com/v3/place/text",
            params={
                "key": AMAP_MAPS_API_KEY,
                "keywords": keywords,
                "city": city,
                "citylimit": citylimit
            }
        )
        response.raise_for_status()
        data = response.json()
        
        if data["status"] != "1":
            return {"error": f"Text Search failed: {data.get('info') or data.get('infocode')}"}
            
        suggestion_cities = []
        if data.get("suggestion", {}).get("cities"):
            for city in data["suggestion"]["cities"]:
                suggestion_cities.append({"name": city.get("name")})
                
        pois = []
        for poi in data.get("pois", []):
            pois.append({
                "id": poi.get("id"),
                "name": poi.get("name"),
                "address": poi.get("address"),
                "typecode": poi.get("typecode")
            })
            
        return {
            "suggestion": {
                "keywords": data.get("suggestion", {}).get("keywords"),
                "cities": suggestion_cities
            },
            "pois": pois
        }
    except requests.exceptions.RequestException as e:
        return {"error": f"Request failed: {str(e)}"}

@mcp.tool()
def maps_around_search(location: str, radius: str = "1000", keywords: str = "") -> Dict[str, Any]:
    """Search for POIs around a location within a specified radius. Location must be in LONGITUDE,LATITUDE format (e.g., '116.397428,39.90923')"""
    try:
        response = requests.get(
            "https://restapi.amap.com/v3/place/around",
            params={
                "key": AMAP_MAPS_API_KEY,
                "location": location,
                "radius": radius,
                "keywords": keywords
            }
        )
        response.raise_for_status()
        data = response.json()
        
        if data["status"] != "1":
            return {"error": f"Around Search failed: {data.get('info') or data.get('infocode')}"}
            
        pois = []
        for poi in data.get("pois", []):
            pois.append({
                "id": poi.get("id"),
                "name": poi.get("name"),
                "address": poi.get("address"),
                "typecode": poi.get("typecode")
            })
            
        return {"pois": pois}
    except requests.exceptions.RequestException as e:
        return {"error": f"Request failed: {str(e)}"}

@mcp.tool()
def maps_search_detail(id: str) -> Dict[str, Any]:
    """Query detailed information for a POI ID obtained from keyword search or nearby search"""
    try:
        response = requests.get(
            "https://restapi.amap.com/v3/place/detail",
            params={
                "key": AMAP_MAPS_API_KEY,
                "id": id
            }
        )
        response.raise_for_status()
        data = response.json()
        
        if data["status"] != "1":
            return {"error": f"Get poi detail failed: {data.get('info') or data.get('infocode')}"}
            
        if not data.get("pois"):
            return {"error": "No POI found"}
            
        poi = data["pois"][0]
        result = {
            "id": poi.get("id"),
            "name": poi.get("name"),
            "location": poi.get("location"),
            "address": poi.get("address"),
            "business_area": poi.get("business_area"),
            "city": poi.get("cityname"),
            "type": poi.get("type"),
            "alias": poi.get("alias")
        }
        
        # Add biz_ext data if available
        if poi.get("biz_ext"):
            result.update(poi["biz_ext"])
            
        return result
    except requests.exceptions.RequestException as e:
        return {"error": f"Request failed: {str(e)}"}

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Amap MCP Server")
    parser.add_argument('transport', nargs='?', default='stdio', choices=['stdio', 'sse', 'streamable-http'],
                        help='Transport type (stdio, sse, or streamable-http)')
    args = parser.parse_args()
    
    # Run the MCP server with the specified transport
    mcp.run(transport=args.transport)