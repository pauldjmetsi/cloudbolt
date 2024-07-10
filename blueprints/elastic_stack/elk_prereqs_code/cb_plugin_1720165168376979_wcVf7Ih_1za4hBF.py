"""
This code runs the ELK script on the target server
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
            ## Elastic Stack Install
            # https://www.howtoforge.com/tutorial/ubuntu-elastic-stack/
            
            ###################
            ## Set variables ##
            ###################
            ELASTIC_IP=$(ip -o -4 addr list ens160 | awk '{print $4}' | cut -d/ -f1)
            ELASTIC_VM_NAME=$HOSTNAME
            KIBANA_USER=metsi
            KIBANA_USER_PASSWORD=Mets1Tech
            ELASTIC_DNS_NAME=elk.metsilabs.local
            
            ###################
            ## Prerequisites ##
            ###################
            
            # Function to check and remove locks
            remove_locks() {
                sudo rm -f /var/lib/dpkg/lock-frontend
                sudo rm -f /var/lib/dpkg/lock
                sudo dpkg --configure -a
            }
            
            # Remove any existing locks
            remove_locks
            
            # Update Ubuntu
            sudo apt-get update -y || { echo "Failed to update package list"; exit 1; }
            
            # Add apt-transport-https for securing software install
            sudo apt-get install -y apt-transport-https || { echo "Failed to install apt-transport-https"; exit 1; }

            # Add the GPG key and repository of the Elastic stack
            wget -qO - https://artifacts.elastic.co/GPG-KEY-elasticsearch | sudo apt-key add - || { echo "Failed to add GPG key"; exit 1; }
            echo "deb https://artifacts.elastic.co/packages/7.x/apt stable main" | sudo tee -a /etc/apt/sources.list.d/elastic-7.x.list
            
            # Add hostname and internal IP to hosts file
            echo "$ELASTIC_IP $ELASTIC_VM_NAME" | sudo tee -a /etc/hosts
            echo "$ELASTIC_IP $ELASTIC_DNS_NAME" | sudo tee -a /etc/hosts
            
            # Update Ubuntu
            sudo apt-get update -y || { echo "Failed to update package list"; exit 1; }
            
            ########################################
            ## Install and configure Elasticsearch ##
            ########################################
            # Install Elasticsearch
            sudo apt-get install -y elasticsearch || { echo "Failed to install Elasticsearch"; exit 1; }
            
            # Update elasticsearch.yml
            sudo sed -i -e "s/#node.name: node-1/node.name: ${ELASTIC_VM_NAME}/g" /etc/elasticsearch/elasticsearch.yml
            sudo sed -i -e "s/#network.host: 192.168.0.1/network.host: ${ELASTIC_IP}/g" /etc/elasticsearch/elasticsearch.yml
            sudo sed -i -e 's/#http.port: 9200/http.port: 9200/g' /etc/elasticsearch/elasticsearch.yml
            sudo sed -i -e "s/#cluster\.initial_master_nodes: \[\"node-1\", \"node-2\"\]/cluster.initial_master_nodes: \[\"${ELASTIC_VM_NAME}\"\]/g" /etc/elasticsearch/elasticsearch.yml

            # Enable Elastic security
            echo "xpack.security.enabled: true" | sudo tee -a /etc/elasticsearch/elasticsearch.yml
            
            # Reload systemd service manager
            sudo systemctl daemon-reload
            
            # Start Elasticsearch service and add to system boot
            sudo systemctl start elasticsearch || { echo "Failed to start Elasticsearch"; exit 1; }
            sudo systemctl enable elasticsearch
            
            # Generate password for the built-in users on Elasticsearch
            yes | sudo /usr/share/elasticsearch/bin/elasticsearch-setup-passwords auto -u "http://${ELASTIC_IP}:9200" > elastic_passwords.txt
            
            # Save password as variables
            PASSWORD_ELASTIC=$(grep "PASSWORD elastic = " elastic_passwords.txt | awk -F'= ' '{print $2}')
            PASSWORD_KIBANA_SYSTEM=$(grep "PASSWORD kibana_system = " elastic_passwords.txt | awk -F'= ' '{print $2}')
            PASSWORD_KIBANA=$(grep "PASSWORD kibana = " elastic_passwords.txt | awk -F'= ' '{print $2}')
            
            echo "PASSWORD_ELASTIC = $PASSWORD_ELASTIC"
            echo "PASSWORD_KIBANA_SYSTEM = $PASSWORD_KIBANA_SYSTEM"
            echo "PASSWORD_KIBANA = $PASSWORD_KIBANA"
            
            # Test Elasticsearch installation
            curl -X GET -u elastic:$PASSWORD_ELASTIC "http://${ELASTIC_IP}:9200/?pretty"
            
            ##################################
            ## Install and configure Kibana ##
            ##################################
            # Install Kibana
            sudo apt-get install -y kibana || { echo "Failed to install Kibana"; exit 1; }
            
            # Edit kibana.yml file
            sudo sed -i -e 's/#server.port: 5601/server.port: 5601/g' /etc/kibana/kibana.yml
            sudo sed -i -e "s/#server.host: \"localhost\"/server.host: \"${ELASTIC_IP}\"/g" /etc/kibana/kibana.yml
            sudo sed -i -e "s/#server.name: \"your-hostname\"/server.name: \"${ELASTIC_VM_NAME}\"/g" /etc/kibana/kibana.yml
            sudo sed -i -e 's/#server.publicBaseUrl: ""/server.publicBaseUrl: ""/g' /etc/kibana/kibana.yml
            sudo sed -i -e "s|#elasticsearch\.hosts: \[\"http://localhost:9200\"\]|elasticsearch.hosts: [\"http://${ELASTIC_IP}:9200\"]|g" /etc/kibana/kibana.yml
            
            # Uncomment elasticsearch.username and elasticsearch.password
            sudo sed -i -e 's/#elasticsearch.username: "kibana_system"/elasticsearch.username: "kibana_system"/g' /etc/kibana/kibana.yml
            sudo sed -i -e "s/#elasticsearch.password: \"pass\"/elasticsearch.password: \"${PASSWORD_KIBANA_SYSTEM}\"/g" /etc/kibana/kibana.yml
            
            # Reload systemd service manager
            sudo systemctl daemon-reload
            
            # Start Kibana service and add to system boot
            sudo systemctl start kibana || { echo "Failed to start Kibana"; exit 1; }
            sudo systemctl enable kibana
            
            # Create new Kibana user
            curl -X POST -u elastic:$PASSWORD_ELASTIC "http://${ELASTIC_IP}:9200/_security/user/${KIBANA_USER}?pretty" -H 'Content-Type: application/json' -d "
            {
              \"password\" : \"${KIBANA_USER_PASSWORD}\",
              \"roles\" : [ \"kibana_admin\" ]
            }"
            
            #############################################
            ## Setup Nginx as reverse proxy for Kibana ##
            #############################################
            # Install nginx
            sudo apt-get install -y nginx || { echo "Failed to install Nginx"; exit 1; }

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
            
            # Activate Nginx virtual host for Kibana
            sudo ln -s /etc/nginx/sites-available/kibana /etc/nginx/sites-enabled/
            
            # Verify Nginx config
            sudo nginx -t || { echo "Nginx configuration test failed"; exit 1; }
            
            # Restart Nginx service
            sudo systemctl restart nginx || { echo "Failed to restart Nginx"; exit 1; }
        """
        result1 = server.execute_script(script_contents=script1, runas_username=server_username, runas_password=server_password, timeout=300)
        set_progress(f"Result1 = {result1}")
        
    return "SUCCESS", "ELK Completed", ""