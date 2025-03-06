import os
import yaml

# Pfad zum Ordner mit den OVPN-Dateien
ovpn_dir = 'ovpns'

# Hole alle Dateien, die mit .ovpn enden
ovpn_files = [f for f in os.listdir(ovpn_dir) if f.endswith('.ovpn')]
ovpn_files.sort()  # Für eine konsistente Reihenfolge

# --- .env Datei erstellen ---
env_lines = [
    "# OpenVPN Configuration",
    "VPN_USER= # Surfshark OpenVPN username",
    "VPN_PASS= # Surfshark OpenVPN password",
    "",
    "# OVPN Files - Each corresponds to a different VPN server"
]

# Für jede OVPN-Datei eine Variable definieren
for i, filename in enumerate(ovpn_files, start=1):
    env_var = "OVPN" if i == 1 else f"OVPN{i}"
    # Hier wird nur der Dateiname (z.B. jp-free-10.protonvpn.tcp.ovpn) eingetragen
    env_lines.append(f"{env_var}={filename}")

# Schreibe die .env Datei
with open('.env', 'w') as env_file:
    env_file.write("\n".join(env_lines))

print(".env wurde erstellt.")

# --- docker-compose.yml erstellen ---
compose = {
    'version': '3.8',
    'services': {},
    'networks': {
        'global': {
            'driver': 'bridge',
            'ipam': {
                'config': [{'subnet': '10.47.0.0/24'}]
            }
        }
    }
}

# Start-IP (letztes Oktett) für rotate-Services
start_ip = 100

for i, filename in enumerate(ovpn_files, start=1):
    service_name = f'rotate{i}'
    ip_address = f'10.47.0.{start_ip + i - 1}'
    # Für den ersten Service soll der env Key "OVPN" genutzt werden, danach "OVPN2", etc.
    env_key = "OVPN" if i == 1 else f"OVPN{i}"
    service = {
        'build': {
            'context': '.',
            'dockerfile': 'dockerfiles/Dockerfile.openvpn',
            'args': [
                'VPN_USER=${VPN_USER}',
                'VPN_PASS=${VPN_PASS}',
                f'OVPN=${{{env_key}}}'
            ]
        },
        'image': f'tatu-rotate-{i}:v1',
        'restart': 'always',
        'hostname': service_name,
        'cap_add': ['NET_ADMIN'],
        'networks': {
            'global': {
                'ipv4_address': ip_address
            }
        },
        'dns': [ "8.8.8.8", "1.1.1.1" ],
        'devices': ['/dev/net/tun:/dev/net/tun']
    }
    compose['services'][service_name] = service

# "mubeng"-Service, der von allen rotate-Services abhängt
rotate_services = list(compose['services'].keys())
mubeng_service = {
    'image': 'ghcr.io/kitabisa/mubeng:latest',
    'volumes': ['./config-templates:/data'],
    'command': '-a :8080 -f /data/proxies.txt -m sequent -r 1',
    'ports': ['8080:8080'],
    'depends_on': rotate_services,
    'restart': 'always',
    'cap_add': ['NET_ADMIN'],
    'networks': {
        'global': {
            'ipv4_address': '10.47.0.200'
        }
    },
    'dns': [ "8.8.8.8", "1.1.1.1" ]
}

compose['services']['mubeng'] = mubeng_service

# Schreibe die docker-compose.yml
with open('docker-compose.yml', 'w') as compose_file:
    yaml.dump(compose, compose_file, sort_keys=False)

print("docker-compose.yml wurde erstellt.")
