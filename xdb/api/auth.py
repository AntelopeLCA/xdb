from antelope.models.auth import AuthorizationGrant, JwtGrant

from typing import Optional

from .runtime import cat, MASTER_ISSUER
from datetime import datetime
from jose import JWTError, ExpiredSignatureError, jwt
from fastapi import HTTPException

import logging


def get_token_command(token: Optional[str]):
    """
    This is used to validate a token signed by the master issuer. In this case, the 'grants' property contains
    a command and arguments
    :param token:
    :return:
    """
    if token is None:
        return []
    try:
        iss = cat.pubkeys[MASTER_ISSUER]
        if iss.expiry < datetime.now().timestamp():
            raise HTTPException(503, detail="Master issuer certificate is expired")
        pub = iss.public_key
    except KeyError:
        logging.info('pubkey MISSING for %s' % MASTER_ISSUER)
        logging.info('avl pubkeys %s' % list(cat.pubkeys.keys()))
        raise HTTPException(503, detail="Master Issuer key is missing or invalid")
    try:
        valid_payload = jwt.decode(token, pub, algorithms=['RS256'])
    except ExpiredSignatureError:
        raise HTTPException(400, detail="Token expired")
    except JWTError:
        raise HTTPException(400, detail="Command token is invalid")
    grant = JwtGrant(**valid_payload)
    return grant.grants.split(':')


def _get_all_grants(user: str):
    """
    generate AuthorizationGrants for every interface
    :param user:
    :return:
    """
    ag = []
    for iface in cat.interfaces:
        o, i = iface.split(':')
        ag.append(AuthorizationGrant(user=user, origin=o, access=i, values=True, update=False))
    return ag


def get_token_grants(token: Optional[str]):
    """
    Returns a 2-tuple: token ID, list of grants
    :param token:
    :return:
    """
    if token is None:
        return '', []
    try:
        payload = jwt.decode(token, 'a fish', options={'verify_signature': False})
    except ExpiredSignatureError:
        raise HTTPException(401, detail="Token is expired")
    try:
        iss = cat.pubkeys[payload['iss']]
    except KeyError:
        raise HTTPException(401, detail='Issuer %s unknown' % payload['iss'])
    if iss.expiry < datetime.now().timestamp():
        raise HTTPException(401, detail='Issuer %s certificate is expired. blackbook server must refresh' % payload['iss'])
    pub = iss.public_key  # this tells us the issuer that signed this token
    try:
        valid_payload = jwt.decode(token, pub, algorithms=['RS256'])
    except JWTError:
        raise HTTPException(401, detail='Token failed verification')
    tid = valid_payload.get('tid', '')
    # however, we also need to test whether the issuer is trusted with the requested origin(s). otherwise one
    # compromised key would allow a user to issue a token for any origin (TODO!)
    if payload['iss'] == MASTER_ISSUER:
        return tid, _get_all_grants(user=payload['sub'])
    jwt_grant = JwtGrant(**valid_payload)
    return tid, AuthorizationGrant.from_jwt(jwt_grant)
