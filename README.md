# Pulumi EC2 Kubernetes Setup

This Pulumi project sets up an AWS EC2 instance and installs Kubernetes on it. The instance is configured with a VPC, subnet, security group, and user data script to initialize Kubernetes.

## Prerequisites

1. Install [Pulumi CLI](https://www.pulumi.com/docs/get-started/install/).
2. Install Python 3.10 or later.
3. Install the required Python dependencies by running:
   ```bash
   pip install -r requirements.txt
   ```
4. Configure AWS credentials. You can use the AWS CLI to set up your credentials:
   ```bash
   aws configure
   ```

## Project Structure

```
pulumi-ec2-k8s/
├── [__main__.py](http://_vscodecontentref_/1)          # Main Pulumi program
├── Pulumi.yaml          # Pulumi project configuration
├── Pulumi.dev.yaml      # Stack-specific configuration
├── requirements.txt     # Python dependencies
└── .gitignore           # Git ignore file
```

## Configuration

The project uses Pulumi configuration to set up the instance type and VPC CIDR block. You can set these values using the Pulumi CLI:
```bash
pulumi config set instanceType <instance-type>  # Default: t2.micro
pulumi config set vpcNetworkCidr <cidr-block>  # Default: 10.0.0.0/16
```

## Deployment

Initialize the Pulumi stack:
```bash
pulumi stack init dev
```

**Preview the changes:**
```bash
pulumi preview
```

**Deploy the stack:**
```bash
pulumi up
```
After deployment, Pulumi will output the public IP, hostname, and URL of the EC2 instance.

**Outputs**
```bash
ip: The public IP address of the EC2 instance.
hostname: The public DNS hostname of the EC2 instance.
url: The HTTP URL to access the instance.
```

**Security Group Configuration**
The security group allows the following inbound traffic:
```bash
SSH (Port 22)
HTTP (Port 80)
Kubernetes API Server (Port 6443)
etcd (Ports 2379-2380)
Kube-scheduler and Kube-controller-manager (Ports 10251-10252)
NodePort range for services (Ports 30000-32767)
Kubelet (Port 10250)
```
**Kubernetes Setup**
The EC2 instance is configured to:
```bash
Install containerd.
Install Kubernetes components (kubelet, kubeadm, kubectl).
Disable swap and configure kernel modules for Kubernetes.
Initialize Kubernetes with kubeadm.
Install Flannel as the pod network.
```

**Cleanup**

To destroy the resources created by Pulumi, run:
```bash
pulumi destroy
```