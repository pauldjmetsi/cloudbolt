"""
Installs Kibana 
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
            ## Elastic Stack Install Kibana

            ###################
            ## Set variables ##
            ###################
            ELASTIC_IP=$(ip -o -4 addr list ens160 | awk '{print $4}' | cut -d/ -f1)
            ELASTIC_VM_NAME=$HOSTNAME
            PASSWORD_KIBANA_SYSTEM=$(grep "PASSWORD kibana_system = " elastic_passwords.txt | awk -F'= ' '{print $2}')

            # Function to check and remove locks
            remove_locks() {
                echo Mets1Tech | sudo -S rm -f /var/lib/dpkg/lock-frontend
                sudo rm -f /var/lib/dpkg/lock
                sudo dpkg --configure -a
            }


            ##################################
            ## Install and configure Kibana ##
            ##################################

            # Remove any existing locks
            remove_locks

            echo "INFO: Installing Kibana"
            # Install Kibana
            sudo apt-get install kibana

            echo "INFO: Updating kibana.yaml"
            # Edit kibana.yaml file 
            sudo sed -i -e 's/#server.port: 5601/server.port: 5601/g' /etc/kibana/kibana.yml
            sudo sed -i -e "s/#server\\.host: \\"localhost\\"/server.host: \\"${ELASTIC_IP}\\"/g" /etc/kibana/kibana.yml
            sudo sed -i -e "s/#server\\.name: \\"your-hostname\\"/server.name: \\"${ELASTIC_VM_NAME}\\"/g" /etc/kibana/kibana.yml
            sudo sed -i -e 's/server.publicBaseUrl: ""/#server.publicBaseUrl: ""/g' /etc/kibana/kibana.yml
            sudo sed -i -e "s|#elasticsearch\\.hosts: \[\\"http://localhost:9200\\"\]|elasticsearch.hosts: [\\"http://${ELASTIC_IP}:9200\\"]|g" /etc/kibana/kibana.yml

            # uncomment elasticsearch.password. Get password from set password command. 
            sudo sed -i -e 's/#elasticsearch.username: "kibana_system"/elasticsearch.username: "kibana_system"/g' /etc/kibana/kibana.yml
            sudo sed -i -e "s|#elasticsearch.password: \\"pass\\"|elasticsearch.password: \\"${PASSWORD_KIBANA_SYSTEM}\\"|g" /etc/kibana/kibana.yml

            echo "INFO: Reloading daemon"
            # Reload system 
            sudo systemctl daemon-reload

            echo "INFO: Starting Kibana services"
            # Start Kibana service and add to system boot
            sudo systemctl start kibana
            sudo systemctl enable kibana
        """
        
        result = server.execute_script(script_contents=script1, runas_username=server_username, runas_password=server_password, timeout=300)
        set_progress(f"Result = {result}")
        
    return "SUCCESS", "ELK Completed", ""