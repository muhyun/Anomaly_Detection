import numpy as np
import mxnet as mx
from mxnet import gluon
import glob
import argparse
import os
from six import BytesIO, StringIO

out = 10

class STSAE(gluon.nn.HybridBlock):
    def __init__(self):
        super(STSAE, self).__init__()
        with self.name_scope():
            self.encoder = gluon.nn.HybridSequential(prefix="encoder")
            with self.encoder.name_scope():
                self.encoder.add(gluon.nn.Conv2D(512, kernel_size=15, strides=4, activation='relu'))
                self.encoder.add(gluon.nn.BatchNorm())
                self.encoder.add(gluon.nn.MaxPool2D(2))
                self.encoder.add(gluon.nn.BatchNorm())
                self.encoder.add(gluon.nn.Conv2D(256, kernel_size=4, activation='relu'))
                self.encoder.add(gluon.nn.BatchNorm())
                self.encoder.add(gluon.nn.MaxPool2D(2))
                self.encoder.add(gluon.nn.BatchNorm())
                self.encoder.add(gluon.nn.Conv2D(128, kernel_size=3, activation='relu'))
                self.encoder.add(gluon.nn.BatchNorm())
                
            self.decoder = gluon.nn.HybridSequential(prefix="decoder")
            with self.decoder.name_scope():
                self.decoder.add(gluon.nn.Conv2DTranspose(channels=256, kernel_size=3, activation='relu'))
                self.decoder.add(gluon.nn.BatchNorm())
                self.decoder.add(gluon.nn.HybridLambda(lambda F, x: F.UpSampling(x, scale=2, sample_type='nearest')))
                self.decoder.add(gluon.nn.BatchNorm())
                self.decoder.add(gluon.nn.Conv2DTranspose(channels=512, kernel_size=4, activation='relu'))
                self.decoder.add(gluon.nn.BatchNorm())
                self.decoder.add(gluon.nn.HybridLambda(lambda F, x: F.UpSampling(x, scale=2, sample_type='nearest')))
                self.decoder.add(gluon.nn.BatchNorm())
                self.decoder.add(gluon.nn.Conv2DTranspose(channels=out, kernel_size=15, strides=4, activation='sigmoid'))


    def hybrid_forward(self, F, x):
        x = self.encoder(x)
        x = self.decoder(x)

        return x

ctx = mx.cpu()  

def train(batch_size, epochs, learning_rate, weight_decay):
    
    train = np.load("../input/data/train/input_data.npy")   
    dataset = gluon.data.ArrayDataset(mx.nd.array(train, dtype=np.float32))
    dataloader = gluon.data.DataLoader(dataset, batch_size=batch_size, last_batch='rollover',shuffle=True)
    
    model = STSAE()
    model.hybridize()
    model.collect_params().initialize(mx.init.Normal(0.01), ctx=ctx)

    
    loss2 = gluon.loss.L2Loss()
    
    optimizer = gluon.Trainer(model.collect_params(), 'adam', {'learning_rate': learning_rate, 'wd': weight_decay})
    
    for epoch in range(epochs):

        for img in dataloader:
            
            img = img.as_in_context(ctx)
            batch = img.shape[0]

            with mx.autograd.record():
                output = model(img)
                loss = loss2(output, img)
                
            loss.backward()
            optimizer.step(batch_size)
            print('epoch [{}/{}], loss:{:.4f}'.format(epoch + 1, epochs, mx.nd.mean(loss).asscalar()))
       
    save(model, os.environ['SM_MODEL_DIR'])   
    return model

def save(model, model_dir):
    model.save_parameters('%s/model.params' % model_dir)

def model_fn(model_dir):
    model = STSAE()
    model.load_parameters("%s/model.params" %model_dir, ctx=ctx)
    return model

#def transform_fn(model, data, content_type, accept):
#    tmp = np.load(StringIO(data))
#    mx_nd_array = mx.nd.array(data)
#    mx_nd_array = mx_nd_array.as_in_context(ctx)
#    output = model(mx_nd_array)
#    np_array = output.asnumpy()
#    np.save("output", np_array)
#    f = open("output.npy")
#    return f.read()
    
def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument('--batch_size', type=int, default=100)
    parser.add_argument('--epochs', type=int, default=10)
    parser.add_argument('--learning_rate', type=float, default=0.1)
    parser.add_argument('--wd', type=float, default=0.1)

    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()

    train(args.batch_size, args.epochs, args.learning_rate, args.wd)
        
#def input_fn(input_data, content_type):
    
#def predict_fn(block, array):
