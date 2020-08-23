# This file is executed on every boot (including wake-boot from deepsleep)

# Set CPU frequency
import machine
machine.freq(160000000) # Set to 160MHz for speeeeeeed

# Debugging
import esp
esp.osdebug(None) # turn off vendor O/S debugging messages

# Detach the REPL from UART0
#import uos
#uos.dupterm(None, 1) # disable REPL on UART(0)

# Web REPL if we choose to use it?
#import webrepl
#webrepl.start()

# Garbage Collection
import gc
gc.collect() # Run garbage collection
gc.enable()  # Enable automatic garbage collection