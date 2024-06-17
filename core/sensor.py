import numpy as np
import sys
sys.path.append('../')

import utils
import geometry

import matplotlib.pyplot as plt
import plotly.graph_objects as go

class Sensor: # sensor points are represented in global coordinate space for this class

    def __init__(self,
                 sensor_type = None,
                 transducer_set = None,
                 sensor_coords = None,
                 aperture_type = None, # transmit_as_receive, extended_aperture, pressure_field, microphone 
                 ):
        self.aperture_type = aperture_type
        self.element_lookup = None
        self.sensors_per_el = None
        self.transducer_set = transducer_set
        if aperture_type == "microphone":
            if sensor_coords is None:
                raise Exception("Please supply sensor coordinates to use a microphone-style sensor mask")
            self.sensor_coords = sensor_coords
        elif aperture_type is None or aperture_type == "pressure_field":
            self.sensor_coords = None
            self.element_lookup = np.array([])
            self.sensors_per_el = np.array([])
        else:
            if transducer_set is None:
                raise Exception("Please supply a transducer set")
            all_sensor_coords = []
            all_element_lookup = []
            element_shift = 0
            sensors_per_el = []
            for key in range(len(transducer_set)):
                t = transducer_set.transducers[key]
                p = transducer_set.poses[key]
                assert p is not None, f"Pose for transducer {key} has not been assigned."
                sensor_coords = t.get_sensor_coords()
                t_element_lookup = np.arange(sensor_coords.shape[0], dtype=np.int64)
                t_sensors_per_el = t.get_sensors_per_el()
                t_element_lookup = t_element_lookup // t_sensors_per_el
                t_element_lookup = np.add(t_element_lookup, element_shift)
                all_element_lookup.append(t_element_lookup)
                global_sensor_coords = p.apply_to_points(sensor_coords, inverse=False) 
                all_sensor_coords.append(global_sensor_coords)
                sensors_per_el.append(np.ones(t.get_num_elements())*t_sensors_per_el)
                element_shift = t_element_lookup[-1] + 1
            self.element_lookup = np.concatenate(all_element_lookup, axis=0)
            self.sensor_coords = np.concatenate(all_sensor_coords, axis=0)
            self.sensors_per_el = np.concatenate(sensors_per_el, axis=0)
            

    @classmethod
    def load(cls, filepath, transducer_set=None):
        sensor = cls()
        my_dict = utils.json_to_dict(filepath)
        for key, value in my_dict.items():
            setattr(sensor, key, value)
        if transducer_set is not None:
            sensor.transducer_set = transducer_set
        else:
            print('loading sensor without transducer set, mind the aperture type!')
        if sensor.sensor_coords is not None:
            sensor.sensor_coords = np.array(sensor.sensor_coords)
        if sensor.element_lookup is not None:
            sensor.element_lookup = np.array(sensor.element_lookup)
        if sensor.sensors_per_el is not None:
            sensor.sensors_per_el = np.array(sensor.sensors_per_el)
        return sensor
    

    def save(self, savefile):
        save_dict = {}
        save_dict['aperture_type'] = self.aperture_type
        save_dict['sensor_coords'] = self.to_list()
        save_dict['element_lookup'] = np.ndarray.tolist(self.element_lookup)
        save_dict['sensors_per_el'] = np.ndarray.tolist(self.sensors_per_el)
        utils.dict_to_json(save_dict, savefile)
        

    def to_list(self, my_list = None):
        if my_list is None:
            if self.sensor_coords is None:
                return None
            my_list = self.sensor_coords
        sensor_coord_list = []
        for coord in my_list:
            sensor_coord_list.append(tuple(coord))
        return sensor_coord_list
    
    def visualize(self, phantom, index=(slice(0, -1, 1), slice(0, -1, 1), 0), body_surface_mask = None):
        # global_mask = phantom.mask.copy()
        # global_mask = np.where(phantom.mask != float(phantom.default_tissue), 1, 0)
        global_mask = np.zeros(phantom.mask.shape)
        sensor_voxels = np.divide(self.sensor_coords, phantom.voxel_dims)
        phantom_centroid = np.array(phantom.mask.shape)//2 
        recenter_matrix = np.broadcast_to(phantom_centroid, sensor_voxels.shape)
        sensor_voxels = sensor_voxels + recenter_matrix
        
        sensor_voxels_disc = np.ndarray.astype(np.round(sensor_voxels), int)
        # if body_surface_mask is not None:
        #     # global_mask = global_mask + body_surface_mask * (np.amax(phantom.mask) + 2)
        #     global_mask = global_mask + body_surface_mask / 2
            
        for voxel in sensor_voxels_disc:
            if np.prod(np.where(voxel >= 0, 1, 0)) == 0: 
                continue
            if np.prod(np.where(voxel < global_mask.shape, 1, 0)) == 0:
                continue
            # global_mask[voxel[0], voxel[1], voxel[2]] = np.amax(phantom.mask) + 1
            global_mask[voxel[0], voxel[1], voxel[2]] = 1
        
        plt.imshow(phantom.mask[tuple(index)] + global_mask[tuple(index)], cmap='gray')
        plt.imshow(np.stack((np.zeros_like(global_mask[tuple(index)]),
                             global_mask[tuple(index)]*255,
                             global_mask[tuple(index)]*255,
                             global_mask[tuple(index)]*255), axis=-1))

    
    # takes in a list of sensor coords (global coordinate system), transforms to match reference of transmit transducer, and discretizes
    def make_sensor_mask(self, sim_transducer, not_transducer, grid_voxel_size, transmit_transform = None):
        if type(sim_transducer).__name__ == "Focused" and self.aperture_type == "transmit_as_receive":
            sensor_mask = not_transducer.indexed_mask
            sensor_mask = np.where(sensor_mask > 0, 1, sensor_mask)
            discretized_sensor_coords = None
        else:
            sensor_mask = np.zeros(not_transducer.indexed_mask.shape)
            if self.aperture_type == "pressure_field":
                sensor_mask[:, :, sensor_mask.shape[2]//2] = 1
                discretized_sensor_coords = None
            else:
                if transmit_transform is None:
                    raise Exception("Please supply a transmit transducer affine transformation")
                transformed_sensor_coords = transmit_transform.apply_to_points(self.sensor_coords, inverse=True)
                transformed_sensor_coords = np.divide(transformed_sensor_coords, grid_voxel_size)
                mask_centroid = np.array(sensor_mask.shape)/2
                mask_centroid[0] = 0
                recenter_matrix = np.broadcast_to(mask_centroid, transformed_sensor_coords.shape)
                transformed_sensor_coords = transformed_sensor_coords + recenter_matrix
                discretized_sensor_coords = np.ndarray.astype(np.round(transformed_sensor_coords), int)
                for coord in discretized_sensor_coords:
                    if np.prod(np.where(coord >= 0, 1, 0)) == 0: 
                        continue
                    if np.prod(np.where(coord < sensor_mask.shape, 1, 0)) == 0:
                        continue
                    sensor_mask[coord[0], coord[1], coord[2]] = 1
        return sensor_mask, discretized_sensor_coords


    # takes sensor data and aggregates voxel-level data into element-level data
    def voxel_to_element(self, sim_properties, transmit, discretized_sensor_coords, sensor_data, additional_keys):
        computational_grid_size = (np.array(sim_properties.matrix_size) - 2 * np.array(sim_properties.PML_size))
        data = sensor_data['p'].T
        if type(transmit).__name__ == "Focused" and self.aperture_type == "transmit_as_receive":
            signals = transmit.not_transducer.combine_sensor_data(data)
            other_signals = []
            for other_key in additional_keys:
                other_signals.append(sensor_data[other_key])
        else:
            # omissions
            condensed_discrete_coords = discretized_sensor_coords[np.where(
                [np.logical_and(
                    np.prod(np.where(discretized_sensor_coords[i] >= 0, 1, 0)) != 0,
                    np.prod(np.where(discretized_sensor_coords[i] <  computational_grid_size, 1, 0)) != 0,)
                for i in range(len(discretized_sensor_coords))],
            )]
                                            
            # hashing
            hash_list = np.sum(condensed_discrete_coords * np.array([1,computational_grid_size[0], computational_grid_size[0] * computational_grid_size[1]]), axis=1)
            # collisions
            hash_list = np.unique(hash_list)
            # sorting
            hash_list = np.array(sorted(hash_list))
                        
            sensor_point_signals = np.array([self.hash_fn(coord, hash_list, data, computational_grid_size) for coord in discretized_sensor_coords])
            
            if self.aperture_type == "microphone":
                return sensor_point_signals
                                
            signals = np.zeros([len(self.sensors_per_el), data.shape[1]])
            count = 0
            for i, points in enumerate(list(self.sensors_per_el)):
                signals[i] = np.mean(sensor_point_signals[int(count) : int(count + points)], axis=0)
                count += points
                
            other_signals = []
            for other_key in additional_keys:
                other_signals.append(sensor_data[other_key])
        
        return signals, other_signals
    
    def hash_fn(self, coord, hash_list, data, computational_grid_size):
                if np.logical_or(
                    np.prod(np.where(coord >= 0, 1, 0)) == 0,
                    np.prod(np.where(coord < computational_grid_size, 1, 0)) == 0,):
                    return np.zeros(data[0].shape)
                hash_val = np.sum(coord * np.array([1, computational_grid_size[0], computational_grid_size[0] * computational_grid_size[1]]))
                index = np.where(hash_list == hash_val)[0][0]
                return data[index]
            
    def sort_pressure_field(self, sensor_data, additional_keys, grid_shape):
        signals = sensor_data['p'].T.reshape(grid_shape[1],grid_shape[0],-1).transpose(1,0,2)
        other_signals = []
        for other_key in additional_keys:
            other_signals.append(sensor_data[other_key].T.reshape(grid_shape[1],grid_shape[0]).transpose(1,0))
        return signals, other_signals



