import pulumi
import pulumi_aws as aws

# configuration values
config = pulumi.Config()
instance_type = config.get("instanceType")
if instance_type is None:
    instance_type = "t2.micro"
vpc_network_cidr = config.get("vpcNetworkCidr")
if vpc_network_cidr is None:
    vpc_network_cidr = "10.0.0.0/16"

# Ubuntu 24.04 LTS (HVM), SSD Volume Type - ami-084568db4383264d4
ami = "ami-084568db4383264d4"  


# User data 
user_data = """#!/bin/bash
exec > >(tee /var/log/user-data.log | logger -t user-data) 2>&1

# Update and install dependencies
sudo apt update && sudo apt upgrade -y
sudo apt install apt-transport-https curl -y

# Install containerd
sudo apt install containerd -y

echo "sleeping..."
sleep 10

sudo mkdir -p /etc/containerd
containerd config default | sudo tee /etc/containerd/config.toml > /dev/null
sudo sed -i 's/SystemdCgroup = false/SystemdCgroup = true/' /etc/containerd/config.toml
sudo systemctl restart containerd
sudo systemctl enable containerd

# Install Kubernetes
curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.30/deb/Release.key | sudo gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg
echo 'deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v1.30/deb/ /' | sudo tee /etc/apt/sources.list.d/kubernetes.list
sudo apt update
sudo apt install -y kubelet kubeadm kubectl
sudo apt-mark hold kubelet kubeadm kubectl

sudo systemctl enable --now kubelet

# Disable swap permanently
sudo swapoff -a
sudo sed -i '/ swap / s/^\(.*\)$/#\1/g' /etc/fstab

# Load necessary kernel modules
echo -e "overlay\nbr_netfilter" | sudo tee /etc/modules-load.d/k8s.conf

cat <<EOF | sudo tee /etc/modules-load.d/k8s.conf
overlay
br_netfilter
EOF

sudo modprobe overlay
sudo modprobe br_netfilter

# Set sysctl params
cat <<EOF | sudo tee /etc/sysctl.d/k8s.conf
net.bridge.bridge-nf-call-iptables  = 1
net.bridge.bridge-nf-call-ip6tables = 1
net.ipv4.ip_forward                 = 1
EOF
sudo sysctl --system

# Initialize Kubernetes
sudo kubeadm init --pod-network-cidr=10.244.0.0/16

echo "sleeping..."
sleep 10

# Configure kubectl
mkdir -p $HOME/.kube
sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
sudo chown $(id -u):$(id -g) $HOME/.kube/config

echo 'export KUBECONFIG=$HOME/.kube/config' >> ~/.bashrc
source ~/.bashrc

# Configure kubectl for root
mkdir -p /root/.kube
cp -i /etc/kubernetes/admin.conf /root/.kube/config
chown root:root /root/.kube/config

echo 'export KUBECONFIG=/root/.kube/config' >> /root/.bashrc
source ~/.bashrc

echo "sleeping..."
sleep 10

# Configure kubectl for ubuntu user
mkdir -p /home/ubuntu/.kube
cp -i /etc/kubernetes/admin.conf /home/ubuntu/.kube/config
chown ubuntu:ubuntu /home/ubuntu/.kube/config

echo 'export KUBECONFIG=/home/ubuntu/.kube/config' >> /home/ubuntu/.bashrc
source ~/.bashrc

echo "sleeping..."
sleep 10

# Install Flannel with retry logic

kubectl apply -f https://github.com/flannel-io/flannel/releases/latest/download/kube-flannel.yml && break

echo "sleeping..."
sleep 10

sudo pwd

# Verify setup
kubectl get nodes
kubectl get pods --all-namespaces

# Create pods in the default namespace
kubectl taint nodes --all node-role.kubernetes.io/control-plane-

"""



# VPC configuration
vpc = aws.ec2.Vpc(
    "vpc",
    cidr_block=vpc_network_cidr,
    enable_dns_hostnames=True,
    enable_dns_support=True,
)

# internet gateway configuration
gateway = aws.ec2.InternetGateway("gateway", vpc_id=vpc.id)

# subnet configuration
subnet = aws.ec2.Subnet(
    "subnet", vpc_id=vpc.id, 
    cidr_block="10.0.1.0/24",
    availability_zone="us-east-1a", 
    map_public_ip_on_launch=True
)

# route table configuration
route_table = aws.ec2.RouteTable(
    "routeTable",
    vpc_id=vpc.id,
    routes=[
        {
            "cidr_block": "0.0.0.0/0",
            "gateway_id": gateway.id,
        }
    ],
)

# route table association configuration
route_table_association = aws.ec2.RouteTableAssociation(
    "routeTableAssociation", subnet_id=subnet.id, route_table_id=route_table.id
)

# security group configuration
sec_group = aws.ec2.SecurityGroup(
    "secGroup",
    description="Enable HTTP access",
    vpc_id=vpc.id,
    ingress=[
        {
            "from_port": 22, #SSH access to the K8s nodes
            "to_port": 22,
            "protocol": "tcp",
            "cidr_blocks": ["0.0.0.0/0"],
        },
        {
            "from_port": 80, # HTTP access to the web server
            "to_port": 80,
            "protocol": "tcp",
            "cidr_blocks": ["0.0.0.0/0"],
        },
        {
            "from_port": 6443, # k8s API server
            "to_port": 6443,
            "protocol": "tcp",
            "cidr_blocks": ["0.0.0.0/0"],
        },
        {
            "from_port": 2379, # etcd server client API Ports 2379 and 2380 are used for client communication and peer communication, respectively
            "to_port": 2380,
            "protocol": "tcp",
            "cidr_blocks": ["0.0.0.0/0"],
        },
        {
            "from_port": 10251, # kube-scheduler and kube-controller-manager
            "to_port": 10252,
            "protocol": "tcp",
            "cidr_blocks": ["0.0.0.0/0"],
        },
        {
            "from_port": 30000, # NodePort range for services
            "to_port": 32767,
            "protocol": "tcp",
            "cidr_blocks": ["0.0.0.0/0"],
        },
        {
            "from_port": 10250, # kubelet
            "to_port": 10250,
            "protocol": "tcp",
            "cidr_blocks": ["0.0.0.0/0"],
        },
        
    ],
    egress=[
        {
            "from_port": 0,
            "to_port": 0,
            "protocol": "-1",
            "cidr_blocks": ["0.0.0.0/0"],
        }
    ],
)

# EC2 instance configuration
server = aws.ec2.Instance(
    "server",
    instance_type=instance_type,
    subnet_id=subnet.id,
    vpc_security_group_ids=[sec_group.id],
    user_data=user_data,
    ami=ami,
    tags={
        "Name": "k8s-webserver",
    },
)

# instances accessible IP address and hostname
pulumi.export("ip", server.public_ip)
pulumi.export("hostname", server.public_dns)
pulumi.export("url", server.public_dns.apply(lambda public_dns: f"http://{public_dns}"))
