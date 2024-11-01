from autoparadvisor_contrastive import *
import argparse
import pdb

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
dtype = torch.float32

parser = argparse.ArgumentParser('Contrastive model training')
#parser.add_argument('--name', type=str)
#parser.add_argument('--fastqs', nargs='+')
parser.add_argument('--assembler', type=str)
parser.add_argument('--augmentation',type=int,default=1)
args = parser.parse_args()


#training_size = 1263


input_mash_mat_subsample_np = np.load("train_features_withaug_"+args.assembler+".npy")
input_mash_mat_subsample = torch.from_numpy(input_mash_mat_subsample_np).to(dtype=dtype,device=device)

data_size = int(input_mash_mat_subsample_np.shape[0]/8)
input_mash_mat_np = input_mash_mat_subsample_np[np.arange(data_size)*8+7]
input_mash_mat = torch.from_numpy(input_mash_mat_np).to(dtype=dtype,device=device)
#data_size = input_mash_mat.shape[0]

Matrix_subsample = np.load("sim_train_"+args.assembler+".npy")
Matrix_new = Matrix_subsample[np.arange(data_size)*8+7][:,np.arange(data_size)*8+7]

use_subsample = args.augmentation
if use_subsample==1:
    sim_mat = torch.from_numpy(1-2*Matrix_subsample).to(dtype=dtype,device=device)
    assert data_size*8 == sim_mat.shape[0]
else:
    sim_mat = torch.from_numpy(1-2*Matrix_new).to(dtype=dtype,device=device)
    assert data_size == sim_mat.shape[0]

model = Set_Encoder(r_dim=128,h1_dim=128,h2_dim=256,z_dim=64)
criterion = ContrastiveLoss(mode="l2")

if torch.cuda.is_available():
    model = model.cuda()
    criterion = criterion.cuda()

optimizer = optim.Adam(model.parameters(),lr=1e-3)

batch_size = 128
epochs = 401
loss_list = []

for epoch in tqdm.tqdm(range(epochs)):
    #pdb.set_trace()
    #generate input pair
    random_pair_np = np.array([np.random.choice(8,2,replace=False) for i in range(data_size)])
    random_pair = torch.from_numpy(random_pair_np).to(dtype=dtype,device=device)
    model.train()
    losses = AverageMeter()
    batch_time = AverageMeter()
    if use_subsample==1:
        perm_idcs = torch.randperm(data_size*8)
        batch_num = int((8*data_size)/batch_size)
    else:
        perm_idcs = torch.randperm(data_size)
        batch_num = int(data_size/batch_size)
    if batch_num*batch_size <  data_size:
        batch_num+=1
    #batch_num = 1
    #print(batch_num)
    end = time.time()
    for idx in range(batch_num):
        #pdb.set_trace()
        batch_idcs = perm_idcs[idx*batch_size:(idx+1)*batch_size].to(device=device)
        if use_subsample==1:
            #random_pair_batch = random_pair[batch_idcs]
            #batch_pair_idcs = torch.flatten(random_pair_batch+torch.unsqueeze(batch_idcs,1)*8).to(batch_idcs)
            #batch_input = input_mash_mat_subsample[batch_pair_idcs]
            #batch_sim_mat = sim_mat[batch_pair_idcs,:][:,batch_pair_idcs]
            batch_input = input_mash_mat_subsample[batch_idcs]
            batch_sim_mat = sim_mat[batch_idcs,:][:,batch_idcs]
        else:
            batch_input = input_mash_mat[batch_idcs]
            batch_sim_mat = sim_mat[batch_idcs,:][:,batch_idcs]
        #batch_input = input_mash_mat[batch_idcs]
        #batch_sim_mat = sim_mat[batch_idcs,:][:,batch_idcs]
        features = model(batch_input)
        loss = criterion(features,batch_sim_mat)
        losses.update(loss.item(),batch_input.shape[0])
        #pdb.set_trace()
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        batch_time.update(time.time()-end)
        end = time.time()
    print('epoch {}, average loss {:.4f}'.format(epoch, losses.avg))
    loss_list.append(losses.avg)

save_model(model, optimizer, epochs, args.assembler+"_trained_final.pth")
np.save(args.assembler+"_training_loss.npy",np.array(loss_list))