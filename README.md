# Fibonacci-Animated-Seed-Heads
This is a Python scripted project that uses John Zelle's Graphics.py module to produce multi threaded animated seed head patterns. These include those based on the golden mean ratio (or Fibonacci's Rabbit sequence) 0.618 approx.. The sequences are driven by random variations through time, controlling, size, shape, colour and position. 
The script runs 20 threads that each draw seedheads in realtime (RT). 
The actual drawing and undrawing is done from the master or main() thread. All seedhead threads put their commands into a Python queue. These are taken from the queue and passed through graphics.py to be executed by the master thread.
