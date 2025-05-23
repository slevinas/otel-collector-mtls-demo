import uvicorn
from fastapi import FastAPI
from admin_server.otel_setup import setup_otel, meter, tracer
import time

app = FastAPI()
setup_otel()  # initializes OpenTelemetry

@app.get("/hello")
def hello():
    with tracer.start_as_current_span("hello-span"):
        counter = meter.create_counter("hello_requests")

        counter.add(9, attributes={"endpoint": "run_vector_math"})
        time.sleep(1)
        return {"message": "Hello, world!"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
