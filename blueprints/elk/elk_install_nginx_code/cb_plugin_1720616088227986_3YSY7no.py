"""
Installs Nginx
"""
from common.methods import set_progress
from infrastructure.models import Server


def run(job, *args, **kwargs):
    server = kwargs.get('server')
    if server:
        set_progress("This plug-in is running for server {}".format(server))
        
        identified_server = Server.objects.get(id=server.id)
        set_progress(f"identified_server={identified_server} hostname = {identified_server.hostname}")

        server_username = "metsi"
        server_password = "Mets1Tech"
        
        script1 = """ 
            #!/bin/bash
            ## Elastic Stack Install Nginx

            ###################
            ## Set variables ##
            ###################
            ELASTIC_IP=$(ip -o -4 addr list ens160 | awk '{print $4}' | cut -d/ -f1)
            ELASTIC_DNS_NAME=elk.metsilabs.local

            # Function to check and remove locks
            remove_locks() {
                echo Mets1Tech | sudo -S rm -f /var/lib/dpkg/lock-frontend
                sudo rm -f /var/lib/dpkg/lock
                sudo dpkg --configure -a
            }


            #############################################
            ## Setup Nginx as reverse proxy for Kibana ##
            #############################################

            # Remove any existing locks
            remove_locks

            echo "INFO: Installing nginx"
            # Install nginx 
            sudo apt-get install nginx -y

            echo "INFO: Creating new virtual hosts file"
            # Create a new virtual hosts file 'kibana' 
            sudo tee /etc/nginx/sites-available/kibana > /dev/null << EOF
            server {
                listen 80;
            
                server_name ${ELASTIC_DNS_NAME};
            
                location / {
                    proxy_pass http://${ELASTIC_IP}:5601;
                    proxy_http_version 1.1;
                    proxy_set_header Upgrade \$http_upgrade;
                    proxy_set_header Connection 'upgrade';
                    proxy_set_header Host \$host;
                    proxy_cache_bypass \$http_upgrade;
                }
            }
            EOF

            echo "INFO: Activate nginx virtual host for Kibana"
            # Active Ngnix virtual host for Kibana 
            sudo ln -s /etc/nginx/sites-available/kibana /etc/nginx/sites-enabled/

            echo "INFO: Verify nginx"
            # Verify Ngnix config 
            sudo nginx -t

            echo "INFO: Restart nginx service"
            # Restart Ngnix service 
            sudo systemctl restart nginx
        """
        
        result = server.execute_script(script_contents=script1, runas_username=server_username, runas_password=server_password, timeout=300)
        set_progress(f"Result = {result}")
        
    return "SUCCESS", "ELK - Nginx install completed", ""