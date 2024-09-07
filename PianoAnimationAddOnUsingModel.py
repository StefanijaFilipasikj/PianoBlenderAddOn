bl_info = {
    "name": "Piano Animation from Melody on imported object",
    "blender": (4, 0, 0),
    "category": "Animation",
}

import bpy
import mido

class PianoAnimationOperator(bpy.types.Operator):
    bl_idname = "object.piano_animation_operator"
    bl_label = "Create Piano Animation"

    filepath: bpy.props.StringProperty(subtype="FILE_PATH")

    def execute(self, context):
        notes = parse_midi(self.filepath)
        animate_keys(notes)

        if notes:
            last_note = max(notes, key=lambda n: n[2])  # Get the note with the latest end time
            last_frame = convert_time_to_frame(last_note[2])
            bpy.context.scene.frame_end = last_frame
            bpy.context.scene.frame_start = 0

        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

def menu_func(self, context):
    self.layout.operator(PianoAnimationOperator.bl_idname)

def register():
    bpy.utils.register_class(PianoAnimationOperator)
    bpy.types.VIEW3D_MT_object.append(menu_func)

def unregister():
    bpy.utils.unregister_class(PianoAnimationOperator)
    bpy.types.VIEW3D_MT_object.remove(menu_func)

if __name__ == "__main__":
    register()

def parse_midi(file_path):
    midi = mido.MidiFile(file_path)
    notes = []
    note_times = {}
    current_time = 0

    for msg in midi:
        current_time += msg.time
        if msg.type == 'note_on' and msg.velocity > 0:
            note = msg.note
            if note not in note_times:
                note_times[note] = []
            note_times[note].append({'start': current_time})
        elif (msg.type == 'note_off') or (msg.type == 'note_on' and msg.velocity == 0):
            note = msg.note
            if note in note_times and note_times[note]:
                note_info = note_times[note].pop(0)
                note_info['end'] = current_time
                notes.append((note, note_info['start'], note_info['end']))

    return notes

def convert_time_to_frame(time, fps=24):
    return int(time * fps)

def animate_keys(notes):
    fps = 24  # Frames per second
    press_duration_frames = 1  # Frames taken to press the key down
    release_duration_frames = 1  # Frames taken to release the key
    key_depth = 0.015  # Depth to which the key is pressed down


    collection_name = "Piano"
    collection = bpy.data.collections.get(collection_name)

    for note, start_time, end_time in notes:
        key_object = bpy.data.objects.get(f"WhiteKey_{note}") or bpy.data.objects.get(f"BlackKey_{note}")
        
#        key_name = f"WhiteKey_{note}" if note % 12 not in [1, 3, 6, 8, 10] else f"BlackKey_{note}"
#        key_object = collection.objects.get(key_name)

        if key_object and start_time < end_time:
            start_frame = convert_time_to_frame(start_time, fps)
            end_frame = convert_time_to_frame(end_time, fps)

            # Making sure end_frame is after start_frame + press and release durations
            min_end_frame = start_frame + press_duration_frames + release_duration_frames + 1
            if end_frame < min_end_frame:
                end_frame = min_end_frame

            original_z = key_object.location.z

            # Rest position
            key_object.location.z = original_z
            key_object.keyframe_insert(data_path="location", frame=start_frame - 1)

            # Press down
            key_object.location.z = original_z - key_depth
            key_object.keyframe_insert(data_path="location", frame=start_frame + press_duration_frames)

            # Hold down
            key_object.location.z = original_z - key_depth
            key_object.keyframe_insert(data_path="location", frame=end_frame - release_duration_frames)

            # Release up
            key_object.location.z = original_z
            key_object.keyframe_insert(data_path="location", frame=end_frame)

            # Setting interpolation to linear
            if key_object.animation_data and key_object.animation_data.action:
                for fcurve in key_object.animation_data.action.fcurves:
                    for keyframe_point in fcurve.keyframe_points:
                        keyframe_point.interpolation = 'LINEAR'