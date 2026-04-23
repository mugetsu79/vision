morya@printer vision % CAMERA_ONE_ID="$(
  curl -s -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8000/api/v1/cameras |
  CAMERA_NAME='CAMERA1' python3 -c 'import json,os,sys; name=os.environ["CAMERA_NAME"]; cameras=json.load(sys.stdin); match=next((camera["id"] for camera in cameras if camera["name"] == name), ""); print(match)'
)"
echo "$CAMERA_ONE_ID"
Traceback (most recent call last):
  File "<string>", line 1, in <module>
  File "<string>", line 1, in <genexpr>
TypeError: string indices must be integers, not 'str'

morya@printer vision % curl -s -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8000/api/v1/cameras | \
python3 -c 'import json,sys; cameras=json.load(sys.stdin); [print(c["name"], c["id"]) for c in cameras]'
Traceback (most recent call last):
  File "<string>", line 1, in <module>
TypeError: string indices must be integers, not 'str'
morya@printer vision % 
morya@printer vision % 
morya@printer vision % 
morya@printer vision % morya@printer vision % CAMERA_ONE_ID="$(
  curl -s -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8000/api/v1/cameras |
  CAMERA_NAME='CAMERA1' python3 -c 'import json,os,sys; name=os.environ["CAMERA_NAME"]; cameras=json.load(sys.stdin); match=next((camera["id"] for camera in cameras if camera["name"] == name), ""); print(match)'
)"
echo "$CAMERA_ONE_ID"
Traceback (most recent call last):
  File "<string>", line 1, in <module>
  File "<string>", line 1, in <genexpr>
TypeError: string indices must be integers, not 'str'

morya@printer vision % curl -s -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8000/api/v1/cameras | \
python3 -c 'import json,sys; cameras=json.load(sys.stdin); [print(c["name"], c["id"]) for c in cameras]'
Traceback (most recent call last):
  File "<string>", line 1, in <module>
TypeError: string indices must be integers, not 'str'
morya@printer vision %
