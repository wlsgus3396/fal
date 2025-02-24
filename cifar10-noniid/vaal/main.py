import torch
from torchvision import datasets, transforms, models
import torch.utils.data.sampler  as sampler
import torch.utils.data as data
import torch.nn as nn

import numpy as np
import argparse
import random
import os

from custom_datasets import *
import model
import resnet
from solver import Solver
from solver_2 import Solver2
from utils import *
import arguments
import copy
from FedAVG import FedAvg




def seed_worker(worker_id):
    worker_seed = torch.initial_seed() % 2**32
    np.random.seed(worker_seed)
    random.seed(worker_seed)

def cifar_transformer():
    return transforms.Compose([
            transforms.ToTensor(),
            transforms.Normalize((0.4914, 0.4822, 0.4465), (0.2023, 0.1994, 0.2010))
        ])
def mnist_transformer():
    return torchvision.transforms.Compose([
           torchvision.transforms.ToTensor(),
           transforms.Normalize((0.286), (0.353))
       ])
def main(args):
    if args.dataset == 'cifar10':
        test_dataloader = data.DataLoader(
                datasets.CIFAR10(args.data_path, download=True, transform=cifar_transformer(), train=False),
            batch_size=args.batch_size, drop_last=False,worker_init_fn=seed_worker)

        train_dataset = CIFAR10(args.data_path)
        untrain_dataset=plain_CIFAR10(args.data_path)
        args.num_images = 50000
        args.num_val = 5000

        args.num_classes = 10
        
    elif args.dataset == 'mnist':
        test_dataloader = data.DataLoader(
                datasets.FashionMNIST(args.data_path, download=True, transform=mnist_transformer(), train=False),
            batch_size=args.batch_size, drop_last=False,worker_init_fn=seed_worker)
        untrain_dataset=plain_MNIST(args.data_path)
        train_dataset = MNIST(args.data_path)
        
        
        args.num_images = 50000
        args.num_val = 5000

        args.num_classes = 10
    elif args.dataset == 'cifar100':
        test_dataloader = data.DataLoader(
                datasets.CIFAR100(args.data_path, download=True, transform=cifar_transformer(), train=False),
             batch_size=args.batch_size, drop_last=False,worker_init_fn=seed_worker)

        train_dataset = CIFAR100(args.data_path)
        untrain_dataset=plain_CIFAR100(args.data_path)
        args.num_images = 50000
        args.num_val = 5000
        args.num_classes = 100

    elif args.dataset == 'imagenet':
        test_dataloader = data.DataLoader(
                datasets.ImageFolder(args.data_path, transform=imagenet_transformer()),
            drop_last=False, batch_size=args.batch_size)

        train_dataset = ImageNet(args.data_path)

        args.num_val = 128120
        args.num_images = 1281167
        args.budget = 64060
        args.initial_budget = 128120
        args.num_classes = 1000
    else:
        raise NotImplementedError


    GPU_NUM = args.gpu # 원하는 GPU 번호 입력
    device = torch.device(f'cuda:{GPU_NUM}' if torch.cuda.is_available() else 'cpu')
    torch.cuda.set_device(device) # change allocation of current GPU
    random_seed=100+1000*args.K
    torch.manual_seed(random_seed)
    np.random.seed(random_seed)
    random.seed(random_seed)
    torch.cuda.manual_seed(random_seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False




    args.budget*=args.num_clients
    all_indices = set(np.arange(args.num_images)) 
    val_indices = random.sample(all_indices, args.num_val) #validation
    val_sampler = data.sampler.SubsetRandomSampler(val_indices)
    
    #all_indices = np.setdiff1d(list(all_indices), val_indices) #exclude
    labeled_indices=[]
    unlabeled_indices=[]
    remaining_indices=[]
    t_unlabeled_indices=all_indices




    accuracy=[]
    Solo_accuracy=[]
    accuracies = []
    
    #Itask_model=vgg.vgg16_bn(num_classes=args.num_classes)

    all_indices1=copy.deepcopy(all_indices)
    unlabeled_indices=noniid(datasets.CIFAR10(args.data_path, download=True, transform=cifar_transformer(), train=True),args.num_clients)
    for k in range(args.num_clients):
        all_indices1=np.setdiff1d(list(all_indices1), unlabeled_indices[k])
        labeled_indices.append(list(random.sample(list(unlabeled_indices[k]), args.initial_budget))) #initial budget
        unlabeled_indices[k]=list(np.setdiff1d(list(unlabeled_indices[k]), labeled_indices[k]))
        accuracies.append(0)
        t_unlabeled_indices=np.setdiff1d(list(t_unlabeled_indices), labeled_indices[k])
    # dataset with labels available
    
    
    val_dataloader = data.DataLoader(train_dataset, 
            batch_size=args.batch_size, drop_last=True)
            








            
    #args.cuda = args.cuda and torch.cuda.is_available()
    args.cuda=torch.cuda.is_available()
    #splits = [0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4]
    ########################################################################









    for iiter in range(args.global_iteration1): 
        random_seed=100+1000*args.K+iiter
        torch.manual_seed(random_seed)
        np.random.seed(random_seed)
        random.seed(random_seed)
        torch.cuda.manual_seed(random_seed)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False
        
        Solo_accuracy.append(0)
        solver=[]
        task_model=[]
        vae=[]
        discriminator=[]
        stop=[]
        
        unlabeled_dataloader=[]
        unlabeled_train_dataloader=[]
        querry_dataloader=[] 
        val_dataloader=[]   
            
            
        Itask_model=resnet.resnet18()
        num_ftrs = Itask_model.linear.in_features
        Itask_model.linear=nn.Linear(num_ftrs,args.num_classes)
        Ivae=model.VAE(args.latent_dim)
        Idiscriminator=model.Discriminator(args.latent_dim)

        

        for k in range(args.num_clients):
                
            solver.append(Solver(args, test_dataloader))
            task_model.append(resnet.resnet18())
            task_model[k].linear=nn.Linear(num_ftrs,args.num_classes)
            task_model[k].load_state_dict(Itask_model.state_dict())
            stop.append(1)
        for k in range(args.num_clients):    
            vae.append(model.VAE(args.latent_dim))
            vae[k].load_state_dict(Ivae.state_dict())
            discriminator.append(model.Discriminator(args.latent_dim))
            discriminator[k].load_state_dict(Idiscriminator.state_dict())
        
        lr=args.lr
        random_seed=200+1000*args.K+iiter
        torch.manual_seed(random_seed)
        np.random.seed(random_seed)
        random.seed(random_seed)
        torch.cuda.manual_seed(random_seed)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False
        AVG_accuracy=0###################################################################################
        n_avg=[]#######################################################################
        for iter in range(args.global_iteration2): 
            # need to retrain all the models on the new images
            # re initialize and retrain the models
            lr*=args.lr_decay
            # need to retrain all the models on the new images
            # re initialize and retrain the models

             
            w_task_model=[]
            w_vae=[]
            w_discriminator=[]
            if iter==0:
                    t_unlabeled_indices.sort()
                    t_unlabeled_sampler = data.sampler.SubsetRandomSampler(t_unlabeled_indices)
                    t_unlabeled_dataloader=data.DataLoader(untrain_dataset, sampler=t_unlabeled_sampler, batch_size=args.batch_size, drop_last=False,worker_init_fn=seed_worker)  
                    
                
            for k in range(args.num_clients):
                     
                print('Current global iteration1: {}'.format(iiter+1))
                print('Current global iteration2: {}'.format(iter+1))
                print('Client: {}'.format(k+1))

                
                if iter==0:
                    unlabeled_indices[k].sort()
                    labeled_indices[k].sort()
                    unlabeled_sampler = data.sampler.SubsetRandomSampler(unlabeled_indices[k])
                    unlabeled_dataloader.append(data.DataLoader(train_dataset, sampler=unlabeled_sampler, batch_size=args.batch_size, drop_last=False,worker_init_fn=seed_worker))  
                    sampler = data.sampler.SubsetRandomSampler(labeled_indices[k])
                    querry_dataloader.append(data.DataLoader(train_dataset, sampler=sampler, batch_size=args.batch_size, drop_last=False,worker_init_fn=seed_worker))
                    unlabeled_train_dataloader.append(data.DataLoader(train_dataset, sampler=unlabeled_sampler, batch_size=args.batch_size, drop_last=False,worker_init_fn=seed_worker))
                    n_avg.append(len(labeled_indices[k]))#################################################
                    val_dataloader.append(data.DataLoader(untrain_dataset, sampler=sampler,batch_size=args.batch_size, drop_last=False))
                

                _,task_model[k],vae[k],discriminator[k],stop[k] = solver[k].train(querry_dataloader[k],val_dataloader[k],task_model[k],vae[k],discriminator[k],unlabeled_dataloader[k],lr,0,iter)
                w_task_model.append(task_model[k].state_dict())
                w_vae.append(vae[k].state_dict())
                w_discriminator.append(discriminator[k].state_dict())
            
            
            
            global_task_model=copy.deepcopy(task_model[0])
            global_task_model.load_state_dict(FedAvg(w_task_model,n_avg))
            global_vae=copy.deepcopy(vae[0])
            global_vae.load_state_dict(FedAvg(w_vae,n_avg))
            global_discriminator=copy.deepcopy(discriminator[0])
            global_discriminator.load_state_dict(FedAvg(w_discriminator,n_avg))
            

            for k in range(args.num_clients):
                task_model[k]=copy.deepcopy(global_task_model)
                vae[k]=global_vae
                discriminator[k]=global_discriminator
            
            
        for k in range(args.num_clients):
            task_model[k] = task_model[k].cuda()    
            AVG_accuracy+= solver[k].test(task_model[k])        
        
        AVG_accuracy=AVG_accuracy/args.num_clients
            
        accuracy.append(AVG_accuracy)
                
                
        
        
        
        random_seed=100+1000*args.K+iiter
        torch.manual_seed(random_seed)
        np.random.seed(random_seed)
        random.seed(random_seed)
        torch.cuda.manual_seed(random_seed)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False
        
        Solo_accuracy.append(0)
        solver=[]
        task_model=[]
        vae=[]
        discriminator=[]
        stop=[]
        
        Itask_model=resnet.resnet18()
        num_ftrs = Itask_model.linear.in_features
        Itask_model.linear=nn.Linear(num_ftrs,args.num_classes)
        Ivae=model.VAE(args.latent_dim)
        Idiscriminator=model.Discriminator(args.latent_dim)

        

        for k in range(args.num_clients):
                
            solver.append(Solver(args, test_dataloader))
            task_model.append(resnet.resnet18())
            task_model[k].linear=nn.Linear(num_ftrs,args.num_classes)
            task_model[k].load_state_dict(Itask_model.state_dict())
            stop.append(1)
        for k in range(args.num_clients):    
            vae.append(model.VAE(args.latent_dim))
            vae[k].load_state_dict(Ivae.state_dict())
            discriminator.append(model.Discriminator(args.latent_dim))
            discriminator[k].load_state_dict(Idiscriminator.state_dict())
        
        lr=args.lr
        random_seed=200+1000*args.K+iiter
        torch.manual_seed(random_seed)
        np.random.seed(random_seed)
        random.seed(random_seed)
        torch.cuda.manual_seed(random_seed)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False
        AVG_accuracy=0###################################################################################
        for iter in range(args.global_iteration2): 
            # need to retrain all the models on the new images
            # re initialize and retrain the models
            lr*=args.lr_decay
            # need to retrain all the models on the new images
            # re initialize and retrain the models

             
            w_task_model=[]
            w_vae=[]
            w_discriminator=[]
            
            for k in range(args.num_clients):
                     
                print('Current global iteration1: {}'.format(iiter+1))
                print('Current global iteration2: {}'.format(iter+1))
                print('Client: {}'.format(k+1))

                

                _,task_model[k],vae[k],discriminator[k],stop[k] = solver[k].train(querry_dataloader[k],val_dataloader[k],task_model[k],vae[k],discriminator[k],unlabeled_dataloader[k],lr,1,iter)
                w_task_model.append(task_model[k].state_dict())
                w_vae.append(vae[k].state_dict())
                w_discriminator.append(discriminator[k].state_dict())
            
            
            
            global_task_model=copy.deepcopy(task_model[0])
            global_task_model.load_state_dict(FedAvg(w_task_model,n_avg))
            global_vae=copy.deepcopy(vae[0])
            global_vae.load_state_dict(FedAvg(w_vae,n_avg))
            global_discriminator=copy.deepcopy(discriminator[0])
            global_discriminator.load_state_dict(FedAvg(w_discriminator,n_avg))
            

            for k in range(args.num_clients):
                task_model[k]=copy.deepcopy(global_task_model)
                vae[k]=global_vae
                discriminator[k]=global_discriminator
            
            
            
            
            
            #if sum(stop)==0:
                #break
            
            
            

        t_sampled_indices = solver[0].sample_for_labeling(task_model,vae, discriminator ,unlabeled_dataloader[k])
        t_unlabeled_indices=list(np.setdiff1d(list(t_unlabeled_indices), list(t_sampled_indices)))
        
        for k in range(args.num_clients):
            sampled_indices = list(set(t_sampled_indices)&set(unlabeled_indices[k]))
            labeled_indices[k] = list(set().union(list(labeled_indices[k]) ,list(sampled_indices)))
            unlabeled_indices[k]=list(np.setdiff1d(list(unlabeled_indices[k]), list(sampled_indices)))
        ########################################################################################################


        solver=[]
        task_model=[]
        vae=[]
        discriminator=[]
        
        random_seed=300+1000*args.K+iiter
        torch.manual_seed(random_seed)
        np.random.seed(random_seed)
        random.seed(random_seed)
        torch.cuda.manual_seed(random_seed)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False
        
        for k in range(args.num_clients):
                
            solver.append(Solver2(args, test_dataloader))
            task_model.append(resnet.resnet18())
            task_model[k].linear=nn.Linear(num_ftrs,args.num_classes)
            
        for k in range(args.num_clients):
            vae.append(model.VAE(args.latent_dim))
            
            discriminator.append(model.Discriminator(args.latent_dim))
            
            
        
        lr=args.lr_solo
        random_seed=400+1000*args.K+iiter
        torch.manual_seed(random_seed)
        np.random.seed(random_seed)
        random.seed(random_seed)
        torch.cuda.manual_seed(random_seed)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False

        for iter in range(1): 
            # need to retrain all the models on the new images
            # re initialize and retrain the models
            lr*=args.lr_decay
            # need to retrain all the models on the new images
            # re initialize and retrain the models

            for k in range(args.num_clients):   
                
                print('Current global iteration1: {}'.format(iiter+1))
                print('Current global iteration2: {}'.format(iter+1))
                print('Client: {}'.format(k+1))
                print('Solo learning')
                
                Soloaccuracy, task_model[k],_,_ = solver[k].train(querry_dataloader[k],val_dataloader[k],task_model[k],vae[k],discriminator[k],unlabeled_dataloader[k],lr,0,iter)
                Solo_accuracy[iiter]+=Soloaccuracy
                
        Solo_accuracy[iiter]=Solo_accuracy[iiter]/args.num_clients


    
        print('Final Fed accuracy at the {}-th global iteration of data is: {:.2f}'.format(iiter+1, AVG_accuracy))
        print('Final Solo accuracy at the {}-th global iteration of data is: {:.2f}'.format(iiter+1, Solo_accuracy[iiter]))
        


    #torch.save(accuracy, os.path.join(args.out_path, args.log_name))
    accuracy = np.array(accuracy)
    A ="\n".join(map(str, accuracy))
    f = open('./results/R_{}_numclients_{}_lr_{}_lr_decay_{}_Fedacc_{}.csv'.format(args.execute,args.num_clients,args.lr,args.lr_decay,args.K),'w')
    f.write(A)
    f.close()

    Solo_accuracy=np.array(Solo_accuracy)
    A ="\n".join(map(str, Solo_accuracy))
    f = open('./results/R_{}_numclients_{}_lr_{}_lr_decay_{}_Soloacc_{}.csv'.format(args.execute,args.num_clients,args.lr,args.lr_decay,args.K),'w')
    f.write(A)
    f.close()

if __name__ == '__main__':
    args = arguments.get_args()
    main(args)

