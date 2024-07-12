"""
Install Elastic Search
"""
import re
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
            ## Elastic Stack Prerequisites Install

            ###################
            ## Set variables ##
            ###################
            ELASTIC_IP=$(ip -o -4 addr list ens160 | awk '{print $4}' | cut -d/ -f1)
            ELASTIC_VM_NAME=$HOSTNAME
            ELASTIC_DNS_NAME=elk.metsilabs.local

            # Function to check and remove locks
            remove_locks() {
                echo Mets1Tech | sudo -S rm -f /var/lib/dpkg/lock-frontend
                sudo rm -f /var/lib/dpkg/lock
                sudo dpkg --configure -a
            }


            ########################################
            ## Install and configure Elaticsearch ##
            ########################################

            # Remove any existing locks
            remove_locks

            echo "INFO: Installing Elasticsearch"
            # Install Elaticsearch
            sudo apt-get install elasticsearch

            echo "INFO: Updating elasticsearch.yml"
            # Update elasticsearch.yml
            sudo sed -i -e "s/#node.name: node-1/node.name: ${ELASTIC_VM_NAME}/g" /etc/elasticsearch/elasticsearch.yml
            sudo sed -i -e "s/#network.host: 192.168.0.1/network.host: ${ELASTIC_IP}/g" /etc/elasticsearch/elasticsearch.yml
            sudo sed -i -e 's/#http.port: 9200/http.port: 9200/g' /etc/elasticsearch/elasticsearch.yml
            sudo sed -i -e "s/#cluster\\.initial_master_nodes: \[\\\"node-1\\\", \\\"node-2\\\"\\]/cluster.initial_master_nodes: \[\\\"${ELASTIC_VM_NAME}\\\"\\]/g" /etc/elasticsearch/elasticsearch.yml
            
            # enable Elastic security by adding the following 
            sudo -- sh -c "echo xpack.security.enabled: true >> /etc/elasticsearch/elasticsearch.yml"

            echo "INFO: Reloading server manager"
            # Reload systemd service manager
            sudo systemctl daemon-reload

            echo "INFO: Starting Elasticsearch"
            # Start elasticsearch service and add to system boot
            sudo systemctl start elasticsearch
            sudo systemctl enable elasticsearch 

            echo "INFO: Creating passwords for Elasticsearch users"
            # Generate password for the built-in users on Elasticsearch 
            yes | sudo  /usr/share/elasticsearch/bin/elasticsearch-setup-passwords auto -u "http://${ELASTIC_IP}:9200" > elastic_passwords.txt

            echo "INFO: Saving password to file"
            # Save password as variables
            PASSWORD_ELASTIC=$(grep "PASSWORD elastic = " elastic_passwords.txt | awk -F'= ' '{print $2}')
            PASSWORD_KIBANA_SYSTEM=$(grep "PASSWORD kibana_system = " elastic_passwords.txt | awk -F'= ' '{print $2}')
            PASSWORD_KIBANA=$(grep "PASSWORD kibana = " elastic_passwords.txt | awk -F'= ' '{print $2}')

            echo "INFO: PASSWORD_ELASTIC = $PASSWORD_ELASTIC"
            echo "INFO: PASSWORD_KIBANA_SYSTEM = $PASSWORD_KIBANA_SYSTEM"
            echo "INFO: PASSWORD_KIBANA = $PASSWORD_KIBANA"

            echo "INFO: Testing Elasticsearch"
            # Test Elasticsearch installation 
            curl -X GET -u elastic:$PASSWORD_ELASTIC "http://${ELASTIC_IP}:9200/?pretty"
        """
        
        result = server.execute_script(script_contents=script1, runas_username=server_username, runas_password=server_password, timeout=300)
        set_progress(f"Result = {result}")
        
        # Extract PASSWORD_ELASTIC from the script output
        match_elastic_pwd = re.search(r'PASSWORD_ELASTIC = (\S+)', result)
        if match_elastic_pwd:
            password_elastic = match_elastic_pwd.group(1)
            set_progress(f"Extracted PASSWORD_ELASTIC: {password_elastic}")
            server.elk_elastic_password = password_elastic
            server.save()
        else:
            set_progress("Failed to extract PASSWORD_ELASTIC from the script output")

        # Extract PASSWORD_KIBANA from the script output
        match_kibana_pwd = re.search(r'PASSWORD_KIBANA = (\S+)', result)
        if match_kibana_pwd:
            password_kibana = match_kibana_pwd.group(1)
            set_progress(f"Extracted PASSWORD_KIBANA: {password_kibana}")
            server.elk_kibana_password = password_kibana
            server.save()
        else:
            set_progress("Failed to extract PASSWORD_KIBANA from the script output")
        
    return "SUCCESS", "ELK - Elastic Search install completed", ""