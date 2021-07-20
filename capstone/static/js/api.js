import {encodeQueryData} from './utils';


export function getApiUrl(api_url, endpoint, params, split_arrays = false) {
  return `${api_url}${endpoint}/?${encodeQueryData(params, split_arrays)}`;
}

export function jsonQuery(url) {
  return fetch(url).then((resp) => {
      if (!resp.ok)
        throw resp;
      return resp.json();
    })
}