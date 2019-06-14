import {encodeQueryData} from './utils';

const api_url = urls.api_root;  // eslint-disable-line

export function getApiUrl(endpoint, params) {
  return `${api_url}${endpoint}/?${encodeQueryData(params)}`;
}

export function apiQuery(url) {
  return fetch(url).then((resp) => {
      if (!resp.ok)
        throw resp;
      return resp.json();
    })
}