
# coding: utf-8

# In[1]:

# %load_ext autoreload
# %autoreload 2
import os
import cPickle as pickle
import numpy as np
from nn1_decouple_feat_cmp_norm_oct_1 import *

import argparse
parser = argparse.ArgumentParser(description='PyTorch test with the model from Sen')
parser.add_argument("--seed", type=int, default=1)
parser.add_argument("--nhidden", type=int, default=50)
parser.add_argument("--use_lstm", action="store_true")
parser.add_argument("--init_range", type=float, default=0.1)
parser.add_argument("--use_cuda", action="store_true")
parser.add_argument("--log_dir", type=str, default="./results/test")
parser.add_argument("--debug", action="store_true")
parser.add_argument("--lr_thresh", type=float, default=1.0)
args = parser.parse_args()
print("args use cuda ", args.use_cuda)

# Set the random seed manually for reproducibility.
print("using seed ", args.seed)
np.random.seed(args.seed)
torch.manual_seed(args.seed)
if torch.cuda.is_available():
    if not args.use_cuda:
        print("WARNING: You have a CUDA device, so you should probably run with --cuda")
    else:
        torch.cuda.manual_seed(args.seed)
        torch.cuda.manual_seed_all(args.seed)
if torch.cuda.is_available() and args.use_cuda:
    use_cuda = True
else:
    use_cuda = False
print("use cuda ", use_cuda)

# regarding logging and debug options
if not os.path.exists(args.log_dir):
    os.makedirs(args.log_dir)
print("debug mode", args.debug)
if args.debug:
    import logging
    logging.basicConfig(filename=args.log_dir + "/num.log",level=logging.DEBUG)

# In[2]:

import sys
sys.path.append("../tuner_utils")
from yellowfin import YFOptimizer


# In[3]:

os.environ['CUDA_VISIBLE_DEVICES']="0"
batch_size = 50
num_classes = 1


# In[4]:

data = pickle.load(open("yf_data.dat", "rb"))
X_train = data['X_train']
X_train_features = data['X_train_features']
Y_marginals = data['Y_marginals']

X_test = data['X_test']
X_test_feature = data['X_test_feature']


# In[5]:

print X_train_features.shape[1], X_test_feature.shape[0]


# ### static analysis on sparsity

# In[6]:

test = X_train_features[1:14001:14000/10, :]
print "check", test.shape, X_train_features.shape
print "sparsity outside", float(test.size) / float(test.shape[0] * test.shape[1])
print "overall sparsity 50", np.sum(np.sum(test, axis=0)!=0)/float(10344)

test = X_train_features[1:14001:14000/40, :]
print "\n check", test.shape, X_train_features.shape
print "sparsity outside", float(test.size) / float(test.shape[0] * test.shape[1])
print "overall sparsity 40", np.sum(np.sum(test, axis=0)!=0)/float(10344)

test = X_train_features[1:14001:14000/50, :]
print "\n check", test.shape, X_train_features.shape
print "sparsity outside", float(test.size) / float(test.shape[0] * test.shape[1])
print "overall sparsity 50", np.sum(np.sum(test, axis=0)!=0)/float(10344)

test = X_train_features[1:14001:14000/200, :]
print "\n check", test.shape, X_train_features.shape
print "sparsity outside", float(test.size) / float(test.shape[0] * test.shape[1])
print "overall sparsity 200", np.sum(np.sum(test, axis=0)!=0)/float(10344)

test = X_train_features[1:14001:14000/250, :]
print "\n check", test.shape, X_train_features.shape
print "sparsity outside", float(test.size) / float(test.shape[0] * test.shape[1])
print "overall sparsity 250", np.sum(np.sum(test, axis=0)!=0)/float(10344)

test = X_train_features[1:14001:14000/1000, :]
print "\n check", test.shape, X_train_features.shape
print "sparsity outside", float(test.size) / float(test.shape[0] * test.shape[1])
print "overall sparsity 1000", np.sum(np.sum(test, axis=0)!=0)/float(10344)



# In[7]:
print("hidden dimension ", args.nhidden)
word_attn = AttentionWordRNN(batch_size=batch_size, num_tokens=5664, embed_size=100, word_gru_hidden=args.nhidden, 
    bidirectional= True, init_range=args.init_range, use_lstm=args.use_lstm)
mix_softmax = MixtureSoftmax(batch_size=batch_size, word_gru_hidden = args.nhidden, feature_dim = X_train_features.shape[1], n_classes=num_classes)
# mix_softmax = MixtureSoftmax(batch_size=batch_size, word_gru_hidden = 50, feature_dim = 0, n_classes=num_classes)


# In[8]:
if use_cuda:
    word_attn.cuda()
    mix_softmax.cuda()


# In[9]:

softmax = nn.Softmax()
sigmoid = nn.Sigmoid()


# In[10]:

learning_rate = 1.0
print("lr thresh", args.lr_thresh)
optimizer = YFOptimizer(mix_softmax.parameters(), beta=0.999, lr=learning_rate, mu=0.0, zero_debias=True, clip_thresh=None, 
                        auto_clip_fac=None, curv_win_width=20, force_non_inc_step=False, lr_grad_norm_thresh=args.lr_thresh)

# word_optmizer = YFOptimizer(word_attn.parameters(), lr=learning_rate, mu=0.0, auto_clip_fac=2.0)
# mix_optimizer = YFOptimizer(mix_softmax.parameters(), lr=learning_rate, mu=0.0, auto_clip_fac=2.0)

criterion = nn.MultiLabelSoftMarginLoss(size_average=True)


# In[11]:
#if use_cuda:
#    word_attn.cuda()
#    mix_softmax.cuda()


# In[12]:

import time
import math

def timeSince(since):
    now = time.time()
    s = now - since
    m = math.floor(s / 60)
    s -= m * 60
    return '%dm %ds' % (m, s)


# In[13]:

def plot_func(log_dir, iter_id, loss_list, local_curv_list, max_curv_list, min_curv_list,
             lr_g_norm_list, lr_g_norm_squared_list, lr_list, dr_list, mu_list, grad_avg_norm_list,
             dist_list, grad_var_list, move_lr_g_norm_list, move_lr_g_norm_squared_list, 
             fast_view_act_list, lr_grad_norm_clamp_act_list):
    def running_mean(x, N):
        cumsum = np.cumsum(np.insert(x, 0, 0)) 
        return (cumsum[N:] - cumsum[:-N]) / N 
    plt.figure()
    plt.semilogy(loss_list, '.', alpha=0.2, label="Loss")
    plt.semilogy(running_mean(loss_list,100), label="Average Loss")
    plt.xlabel('Iterations')
    plt.ylabel('Loss')
    plt.legend()
    plt.grid()
    ax = plt.subplot(111)
    plt.legend(ncol=3, fancybox=True, shadow=True)
    plt.savefig(log_dir + "/fig_loss_iter_" + str(iter_id) + ".pdf")
    plt.close()

    plt.figure()
    plt.semilogy(lr_g_norm_list, label="lr * grad norm")
    plt.semilogy(local_curv_list, label="local curvature")
    plt.semilogy(max_curv_list, label="max curv in win")
    plt.semilogy(min_curv_list, label="min curv in win")
#         plt.semilogy(clip_norm_base_list, label="Clipping Thresh.")
    #plt.semilogy(lr_g_norm_list, label="lr * grad norm")
   # plt.semilogy(lr_g_norm_squared_list, label="lr * grad norm squared")
   # plt.semilogy(move_lr_g_norm_list, label="lr * grad norm move")
   # plt.semilogy(move_lr_g_norm_squared_list, label="lr * grad norm squared move")
    if np.min(lr_g_norm_list) < 1e-9 or np.min(local_curv_list) < 1e-9 or np.min(max_curv_list) < 1e-9 or np.min(min_curv_list) < 1e-9:
      plt.ylim([1e-9, None] )

    plt.title("On local curvature")
    plt.grid()
    ax = plt.subplot(111)
    ax.legend(ncol=2, fancybox=True, shadow=True)
    plt.savefig(log_dir + "/fig_curv_iter_" + str(iter_id) + ".pdf")
    plt.close()

    plt.figure()
    #plt.semilogy(local_curv_list, label="local curvature")
    #plt.semilogy(max_curv_list, label="max curv in win")
    #plt.semilogy(min_curv_list, label="min curv in win")
#         plt.semilogy(clip_norm_base_list, label="Clipping Thresh.")
    plt.semilogy(lr_g_norm_list, label="lr * grad norm")
    #plt.semilogy(lr_g_norm_squared_list, label="lr * grad norm squared")
    plt.semilogy(move_lr_g_norm_list, label="lr * grad norm move")
    #plt.semilogy(move_lr_g_norm_squared_list, label="lr * grad norm squared move")
    if np.min(lr_g_norm_list) < 1e-9 or np.min(move_lr_g_norm_list) < 1e-9:
      plt.ylim([1e-9, None] )
    plt.title("On local curvature")
    plt.grid()
    ax = plt.subplot(111)
    ax.legend(ncol=2, fancybox=True, shadow=True)
    plt.savefig(log_dir + "/fig_move_iter_" + str(iter_id) + ".pdf")
    plt.close()

    plt.figure()
    #plt.semilogy(local_curv_list, label="local curvature")
    #plt.semilogy(max_curv_list, label="max curv in win")
    #plt.semilogy(min_curv_list, label="min curv in win")
#         plt.semilogy(clip_norm_base_list, label="Clipping Thresh.")
    plt.semilogy(lr_g_norm_squared_list, label="lr * grad norm squared")
    plt.semilogy(move_lr_g_norm_squared_list, label="lr * grad norm squared move")
    if np.min(lr_g_norm_squared_list) < 1e-9 or np.min(move_lr_g_norm_squared_list) < 1e-9:
      plt.ylim([1e-9, None] )
    plt.title("On local curvature")
    plt.grid()
    ax = plt.subplot(111)
    ax.legend(ncol=2, fancybox=True, shadow=True)
    plt.savefig(log_dir + "/fig_move_squared_iter_" + str(iter_id) + ".pdf")
    plt.close()

    plt.figure()
    plt.semilogy(lr_list, label="lr min")
    plt.semilogy(dr_list, label="dynamic range")
    plt.semilogy(mu_list, label="mu")
    plt.semilogy(grad_avg_norm_list, label="Grad avg norm")
    plt.semilogy(dist_list, label="Est dist from opt")
    plt.semilogy(grad_var_list, label="Grad variance")
    plt.semilogy(fast_view_act_list, label="fast_view_act lr")
    plt.semilogy(lr_grad_norm_clamp_act_list, label="lr grad norm clamp lr")
    if np.min(grad_var_list) < 1e-9 or np.min(fast_view_act_list) < 1e-9 or np.min(lr_grad_norm_clamp_act_list) < 1e-9:
      plt.ylim([1e-9, None] )
    plt.title('LR='+str(lr_list[-1])+' mu='+str(mu_list[-1] ) )
    plt.grid()
    plt.legend()
    plt.savefig(log_dir + "/fig_hyper_iter_" + str(iter_id) + ".pdf")
    plt.close()


# In[14]:

def train_early_stopping(mini_batch_size, X_train, X_train_feature, y_train, X_test, X_test_feature, word_attn_model, sent_attn_model, 
                         optimizer, loss_criterion, num_epoch, 
                         print_val_loss_every = 1000, print_loss_every = 50, print_figure_every=1000):
    start = time.time()
    loss_full = []
    loss_epoch = []
    accuracy_epoch = []
    loss_smooth = []
    accuracy_full = []
    epoch_counter = 0
    print "mini_batch_size", mini_batch_size
    
    grad_norm_list_250 = []
    grad_norm_list_50 = []
    grad_norm_list_10 = []
    grad_norm_list_1000 = []
    
    move_list = []
    recover_move_list = []
    
    mu_t_list = []
    lr_t_list = []
    
    g = gen_minibatch(X_train, X_train_feature, y_train,  mini_batch_size)
#     g_250 = gen_minibatch(X_train, X_train_feature, y_train,  mini_batch_size=250)
#     g_50 = gen_minibatch(X_train, X_train_feature, y_train,  mini_batch_size=50)
#     g_10 = gen_minibatch(X_train, X_train_feature, y_train,  mini_batch_size=10)
#     g_1000 = gen_minibatch(X_train, X_train_feature, y_train,  mini_batch_size=1000)
    
    # DEBUG
    loss_list = []
    h_max_list = []
    h_min_list = []
    h_list = []
    dist_list = []
    grad_var_list = []
    
    lr_g_norm_list = []
    lr_g_norm_squared_list = []
    
    lr_list = []
    dr_list = []
    mu_list = []
    grad_avg_norm_list = []
    grad_norm_avg_list = []
  
    move_lr_g_norm_list = [] 
    move_lr_g_norm_squared_list = [] 
 
    lr_grad_norm_clamp_act_list = []
    fast_view_act_list = [] 

    plot_figure = plt.figure()
    # END of DEBUG
    
    for i in xrange(1, num_epoch + 1):
        try:
            tokens, features, labels = next(g)
            
#             print labels
#             print 'tokens', tokens

#             optimizer._lr = 0.5

	    if i > 1:	    
              fast_view_act_list.append(4.0/( (math.sqrt(optimizer._global_state["grad_norm_squared"] ) + math.sqrt(optimizer._h_min) )**2 + 1e-6))
              lr_grad_norm_clamp_act_list.append(optimizer._lr_grad_norm_thresh / (math.sqrt(optimizer._global_state["grad_norm_squared"] ) + 1e-6) )

            loss, grad_norm_250 = train_data(tokens, features, labels, word_attn_model, sent_attn_model, optimizer, loss_criterion, cuda=use_cuda, lstm=args.use_lstm)
            loss_s, gn_s = loss, grad_norm_250
    #             print loss
            #acc = test_accuracy_mini_batch(tokens, features, labels, word_attn_model, sent_attn_model)
            #accuracy_full.append(acc)
            #accuracy_epoch.append(acc)
            loss_full.append(loss)
            loss_epoch.append(loss)
            
#             grad_avg_norm_list.append(optimizer._global_state["grad_avg_norm"] / optimizer.zero_debias_factor())
#             grad_norm_avg_list.append(optimizer._global_state["grad_norm_avg"] / optimizer.zero_debias_factor())

            
#             grad_norm_list_250.append(grad_norm_250)
#             tokens1 = [tokens[0][0:50, :].repeat(5, 1), tokens[1][0:50, :].repeat(5, 1) ]
#             features1 = features[0:50, :].repeat(5, 1)
#             labels1 = labels[0:50].repeat(5, 1)
#             _, grad_norm_50 = train_data(tokens1, features1, labels1, word_attn_model, sent_attn_model, optimizer, loss_criterion, do_step=False)
#             grad_norm_list_50.append(grad_norm_50)
#             tokens1 = [tokens[0][0:10, :].repeat(25, 1), tokens[1][0:10, :].repeat(25, 1) ]
#             features1 = features[0:10, :].repeat(25, 1)
#             labels1 = labels[0:10].repeat(25, 1)            
#             _, grad_norm_10 = train_data(tokens1, features1, labels1, word_attn_model, sent_attn_model, optimizer, loss_criterion, do_step=False)
#             grad_norm_list_10.append(grad_norm_10)
           
#             move_list.append(np.exp(optimizer._global_state["lr_grad_norm_avg"] / optimizer.zero_debias_factor() ) )
#             if i > optimizer._curv_win_width + 1:
#                 move_list.append(optimizer._optimizer.param_groups[0]['lr'] * np.sqrt(optimizer._global_state['grad_norm_squared'] ))
#                 recover_move_list.append(optimizer._global_state["lr_grad_norm_avg_min"] )

#                 move_list.append(optimizer._global_state["lr_grad_norm_avg"] / optimizer.zero_debias_factor() )
#                 print move_list
#             recover_move_list.append(optimizer._test_lr_grad)
        
#             print "? ", optimizer._global_state["lr_grad_norm_avg"] / optimizer.zero_debias_factor(), \
#                 optimizer._test_lr_grad
                           
            
#             # Sanity check
#             loss_s1, gn_s1 = train_data(tokens, features, labels, word_attn_model, sent_attn_model, optimizer, loss_criterion, do_step=False)
#             print "sanity ", loss_s, loss_s1, gn_s, gn_s1
            
#             print "optimizer", optimizer._lr, optimizer._mu, #optimizer._h_min, optimizer._h_max, optimizer._dist_to_opt, optimizer._grad_var, loss
#             print loss every n passes
            

            #if i % print_loss_every == 0:
            #    print 'Loss at %d minibatches, %d epoch,(%s) is %f' %(i, epoch_counter, timeSince(start), np.mean(loss_epoch))
            #    print 'Accuracy at %d minibatches is %f' % (i, np.mean(accuracy_epoch))
        except StopIteration:
            epoch_counter += 1
            print 'Reached %d epocs' % epoch_counter
            print 'i %d' % i
            print 'loss_epoch', np.sum(loss_epoch) / X_train.shape[0]
            print "optimizer", optimizer._lr, optimizer._mu, optimizer._h_min, optimizer._h_max, optimizer._dist_to_opt, optimizer._grad_var, optimizer._lr_t, optimizer._mu_t

#             print "word_optimizer", word_optmizer._lr, word_optmizer._mu, word_optmizer._h_min, word_optmizer._h_max, word_optmizer._dist_to_opt, word_optmizer._grad_var
#             print "mix_optimizer", mix_optimizer._lr, mix_optimizer._mu, mix_optimizer._h_min, mix_optimizer._h_max, mix_optimizer._dist_to_opt, mix_optimizer._grad_var
#             print loss_epoch
            #p = test_accuracy_full_batch(X_test, X_test_feature, mini_batch_size, word_attn_model, sent_attn_model)
#             print p
#             print len(p)
#             p = np.ravel(p)
#             pos = []
#             for i, candidate in enumerate(test_candidates):
#                 test_label_index = L_test.get_row_index(candidate)
#                 test_label       = L_test[test_label_index, 0]
#                 if i < len(p) and p[i] > 0.5:
#                     pos.append(candidate)
                
#             (TP, FP, FN) = entity_level_f1(pos, gold_file, ATTRIBUTE, corpus, parts_by_doc_test)
                
            g = gen_minibatch(X_train, X_train_feature, y_train, mini_batch_size)
            loss_epoch = []
            accuracy_epoch = []
            
            with open(log_dir + "/grad_norm_list_250.txt", "w") as f:
                np.savetxt(f, grad_norm_list_250)
            with open(log_dir + "/grad_norm_list_50.txt", "w") as f:
                np.savetxt(f, grad_norm_list_50)
            with open(log_dir + "/grad_norm_list_10.txt", "w") as f:
                np.savetxt(f, grad_norm_list_10)
            with open(log_dir + "/grad_norm_avg.txt", "w") as f:
                np.savetxt(f, grad_norm_avg_list)
            with open(log_dir + "/grad_avg_norm.txt", "w") as f:
                np.savetxt(f, grad_avg_norm_list)
                
            with open(log_dir + "/mu_t_list.txt", "w") as f:
                np.savetxt(f, mu_t_list)
                
            with open(log_dir + "/lr_t_list.txt", "w") as f:
                np.savetxt(f, lr_t_list)
                
            
        # DEBUG
        loss_list.append(loss)
        h_max_list.append(optimizer._h_max)
        h_min_list.append(optimizer._h_min)
        h_list.append(optimizer._global_state['grad_norm_squared'] )
        
        


#         print "done iteration ", i

#         # Test dictionary saving and loading
#         test_dict = optimizer.state_dict().copy()
#         optimizer = YFOptimizer(mix_softmax.parameters(), beta=0.999, lr=learning_rate, mu=0.0, zero_debias=True, clip_thresh=None, 
#                         auto_clip_fac=None, curv_win_width=20, force_non_inc_step=True)
#         optimizer.load_state_dict(test_dict)
        
        
        if i >= 2:
            mu_t_list.append(optimizer._mu_t)
            lr_t_list.append(optimizer._lr_t)
#         print "test in the middle ", h_list[-1], h_max_list[-1], h_min_list[-1]
#         print "curv window ", optimizer._global_state["curv_win"]
        
        dist_list.append(optimizer._dist_to_opt)
        grad_var_list.append(optimizer._grad_var)

        lr_g_norm_list.append(optimizer._lr * np.sqrt(optimizer._global_state['grad_norm_squared'] ) )
        lr_g_norm_squared_list.append(optimizer._lr * optimizer._global_state['grad_norm_squared'] )
        move_lr_g_norm_list.append(optimizer._optimizer.param_groups[0]["lr"] * np.sqrt(optimizer._global_state['grad_norm_squared'] ) )
        move_lr_g_norm_squared_list.append(optimizer._optimizer.param_groups[0]["lr"] * optimizer._global_state['grad_norm_squared'] )

        lr_list.append(optimizer._lr)
        dr_list.append(optimizer._h_max / optimizer._h_min)
        mu_list.append(optimizer._mu)
        grad_avg_norm_list = []
#         if (i % 1000 == 0) and i != 0:
#             with open("h_val.txt", "w") as f:
#                 np.savetxt(f, h_list)
        
        if (i % print_figure_every == 0 and i != 0) or (i == 50 or i == 1000):
            plot_func(log_dir=log_dir, iter_id=i, loss_list=loss_list, 
                 local_curv_list=h_list, max_curv_list=h_max_list, 
                 min_curv_list=h_min_list, lr_g_norm_list=lr_g_norm_list, lr_g_norm_squared_list=lr_g_norm_squared_list, 
                 lr_list=lr_list, dr_list=dr_list, mu_list=mu_list, 
                 grad_avg_norm_list=grad_avg_norm_list,
                 dist_list=dist_list, grad_var_list=grad_var_list, 
                 move_lr_g_norm_list=move_lr_g_norm_list, move_lr_g_norm_squared_list=move_lr_g_norm_squared_list,
                 fast_view_act_list=fast_view_act_list, lr_grad_norm_clamp_act_list=lr_grad_norm_clamp_act_list)
            print "figure plotted"
        # END of DEBUG
        
#     torch.save(word_attn_model, log_dir + "/word_attn.model")
#     torch.save(sent_attn_model, log_dir + "/sent_attn.model")
            
    return loss_full


# 

# In[15]:

log_dir = args.log_dir
if not os.path.isdir(log_dir):
    os.mkdir(log_dir)
loss_full = train_early_stopping(batch_size, X_train, X_train_features, Y_marginals, X_test, X_test_feature, word_attn, mix_softmax, optimizer, 
                                criterion, 300000, 1000, 1000)


# ##### 

# In[ ]:



