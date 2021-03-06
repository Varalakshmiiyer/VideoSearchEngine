import video_utils
import asyncio
import argparse
import pickle
import socket
import time
import random
import os

# Main file for taking a video, and separating it into multiple chunks
# and distributing the work

# Main API is here, more files may be used for the implementation

def get_video_distributor():
    '''
    return the version specified in the configuration to use
    e.g. if there is a basic one and a complex one, the configuration should be able
    to decide which one to use
    '''
    return None

'''
Describe API supported here
'''

async def send_frame(frame_cluster, host, port, cluster_num, filename, total_clusters):
    '''
    Given an array of frames send it to an listening server for further processing. Use pickle
    to serialize the array to a file so it can be sent over the network.
    '''
    asyncio.sleep(random.randint(1,3))
    try:
        # Pickle the array of frames.
        frame_cluster.insert(0, {"file_name": filename, "cluster_num": cluster_num, "total_clusters": total_clusters})
        if not os.path.exists(os.path.dirname(filename)):
            os.makedirs(os.path.dirname(filename))
        filename = "/tmp/VideoSearchEngine/cluster:" + str(cluster_num) + "distributer.pkl"
        f = open(filename,'wb')
        pickle.dump(frame_cluster, f)
        f.close()

        # Create a socket object
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Send pickle file over the network to server.
        print("Sending cluster to worker: " + str(host) + ":" + str(port))
        s.connect((host, port))
        f = open(filename,'rb')
        data = f.read(1024)
        while (data):
            s.send(data)
            data = f.read(1024)
        f.close()
        s.close() 

        # Clean up pickle file, comment out to retain pickle files
        if os.path.isfile(filename):
            try:
                os.remove(filename)
            except OSError as e:  # if failed, report it back to the user
                print ("Error: %s - %s." % (e.filename, e.strerror))
    except Exception as e:
        print(e)
    asyncio.sleep(random.randint(1,3))

async def distribute_frames(frame_cluster, ports_arr, filename):
    '''
    Given an array of frames break into subarrays and send each subarray
    to some server for processing.
    '''
    # loop = asyncio.get_event_loop()
    tasks = [] 
    cluster_num = 0
    for cluster in frame_cluster:
        # Choose a random avaliable worker to send the cluster to
        host_and_port = ports_arr[cluster_num % len(ports_arr)].split(":")
        hostname = host_and_port[0]
        port = int(host_and_port[1])
        tasks.append(asyncio.ensure_future(send_frame(cluster, hostname, port, cluster_num, filename, len(frame_cluster))))
        cluster_num = cluster_num + 1
    await asyncio.wait(tasks)

'''
Example Usage:
    python VideoDistributer.py --video_path ../clips/bunny_clip.mp4 --port_list hannes.cs.washington.edu:24448,hannes.cs.washington.edu:24449
'''

#TODO: Add arguments to: only extract every nth frame, change width/height of captured frames, etc.
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--video_path", help="path of the video",type=str, required=True)
    parser.add_argument("--port_list", help="ports avaliable for workers",type=list, required=True)
    args = parser.parse_args()
    ports = "".join(args.port_list)
    if ports[len(ports)-1] == ",":
        ports = ("".join(args.port_list)[:-1]).split(",")
    else:
        ports = ports.split(",")

    # Get all frames of the video
    frame_clusters = video_utils.get_frames_clusters_from_video(args.video_path)

    # Seperate frames into groups of similiar frames
    #frame_clusters = video_utils.group_semantic_frames(frames)

    # Distrbute each of the groups
    print("Determined " + str(len(frame_clusters)) + " distinct frame clusters.")
    loop = asyncio.get_event_loop()
    loop.run_until_complete(distribute_frames(frame_clusters, ports, args.video_path))
    loop.close()
