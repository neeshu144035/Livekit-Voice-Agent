import inspect
from livekit import api

def main():
    print(dir(api.CreateSIPParticipantRequest))
    print(dir(api.SIPParticipantInfo))

if __name__ == "__main__":
    main()
